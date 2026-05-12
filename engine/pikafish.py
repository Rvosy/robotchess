"""Pikafish 引擎 UCI 子进程封装。

设计目标：
- 隐藏 subprocess 与协议细节，对上层只暴露 new_game / go / quit。
- 启动阶段解析 `option` 行并记录支持的选项，供 ai/factory 决定是否能用 Skill Level。
- 每次 go 都直接发送完整 FEN（不依赖 startpos+moves 累积），避免漏同步。

线程安全：
- 单实例不可并发调用 go。GUI 程序里整局共用一个引擎实例 + AIWorker 串行调用即可。
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path
from typing import Optional


class PikafishError(Exception):
    """引擎相关异常的统一基类（启动失败 / 通信失败 / 超时 / 协议异常）。"""


class PikafishEngine:
    def __init__(
        self,
        exe_path: Path,
        nnue_path: Path,
        threads: int = 1,
        hash_mb: int = 64,
        startup_timeout_sec: float = 10.0,
    ) -> None:
        if not exe_path.exists():
            raise PikafishError(f"Pikafish 可执行文件不存在: {exe_path}")
        if not nnue_path.exists():
            raise PikafishError(f"NNUE 权重文件不存在: {nnue_path}")

        self._exe_path = exe_path
        self._nnue_path = nnue_path
        self._proc: Optional[subprocess.Popen[str]] = None

        # 引擎自报的可用选项名集合（从 `option name xxx ...` 行解析）
        self._available_options: set[str] = set()

        # Windows 下隐藏黑窗口
        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]

        self._proc = subprocess.Popen(
            [str(exe_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,                      # 行缓冲
            cwd=str(exe_path.parent),       # 让引擎能找到同目录的 nnue
            creationflags=creationflags,
        )

        try:
            self._handshake(threads, hash_mb, startup_timeout_sec)
        except Exception:
            self.quit()
            raise

    # ---------- 公开 API ----------

    def supports_option(self, name: str) -> bool:
        """检查引擎是否在 `uci` 阶段声明过该选项（大小写敏感，按 UCI 标准名）。"""
        return name in self._available_options

    def set_option(self, name: str, value: str) -> None:
        """发送 setoption。调用方需自己判断引擎是否支持该选项。"""
        self._send(f"setoption name {name} value {value}")

    def new_game(self) -> None:
        """新对局：清缓存。每开新局必须调一次。"""
        self._send("ucinewgame")
        self._wait_readyok(timeout_sec=5.0)

    def go(self, fen: str, movetime_ms: int) -> str:
        """根据完整 FEN 计算最佳走法，返回 UCI 走法字符串（如 "h2e2"）。

        阻塞直到收到 bestmove 行；超时或进程退出均抛 PikafishError。
        """
        self._send(f"position fen {fen}")
        self._send(f"go movetime {movetime_ms}")

        deadline = time.monotonic() + (movetime_ms / 1000.0) + 2.0
        while True:
            line = self._readline(deadline=deadline)
            if line is None:
                # 区分两种失败：进程已死 vs. 纯超时
                if self._proc is not None and self._proc.poll() is not None:
                    raise PikafishError(
                        f"引擎进程已退出 (exit code {self._proc.returncode})，"
                        f"请检查 NNUE 文件是否与 exe 同目录"
                    )
                raise PikafishError("等待 bestmove 超时")
            if line.startswith("bestmove"):
                parts = line.split()
                if len(parts) < 2:
                    raise PikafishError(f"bestmove 格式异常: {line!r}")
                move = parts[1]
                if move in ("(none)", "0000"):
                    raise PikafishError("引擎返回空走法（可能已被将死或局面非法）")
                return move
            # info / 其它行忽略

    def quit(self) -> None:
        """优雅退出。失败则强杀。忽略关闭管道时常见的 OSError。"""
        if self._proc is None:
            return
        try:
            if self._proc.poll() is None:
                try:
                    self._send("quit")
                except Exception:
                    pass
                try:
                    self._proc.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    self._proc.kill()
                    self._proc.wait(timeout=2.0)
            # 主动关闭管道，避免 __del__ 阶段报 OSError errno 22
            for stream in (self._proc.stdin, self._proc.stdout):
                if stream is not None:
                    try:
                        stream.close()
                    except OSError:
                        pass
        finally:
            self._proc = None

    # ---------- 上下文管理 ----------

    def __enter__(self) -> "PikafishEngine":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.quit()

    # ---------- 内部 ----------

    def _handshake(self, threads: int, hash_mb: int, startup_timeout_sec: float) -> None:
        """发送 uci → 收集 option → 等 uciok → 设置选项 → isready/readyok。"""
        deadline = time.monotonic() + startup_timeout_sec
        self._send("uci")
        while True:
            line = self._readline(deadline=deadline)
            if line is None:
                raise PikafishError("等待 uciok 超时")
            if line.startswith("option name "):
                # 形如: option name Threads type spin default 1 min 1 max 1024
                rest = line[len("option name "):]
                # 取到 " type " 之前的部分作为选项名（保留空格情形如 "Skill Level"）
                if " type " in rest:
                    name = rest.split(" type ", 1)[0].strip()
                else:
                    name = rest.strip().split()[0]
                if name:
                    self._available_options.add(name)
            elif line == "uciok":
                break

        # NNUE 文件：已通过 cwd=exe_path.parent 让引擎在同目录查找，
        # 直接传文件名（不是绝对路径）以规避 Windows 下中文路径经 UTF-8 管道
        # 再被引擎按 ANSI 解码导致 fopen 失败的坑。
        if self.supports_option("EvalFile"):
            self.set_option("EvalFile", self._nnue_path.name)
        if self.supports_option("Threads"):
            self.set_option("Threads", str(threads))
        if self.supports_option("Hash"):
            self.set_option("Hash", str(hash_mb))

        # 设置 EvalFile 后引擎会加载 nnue，需要 isready 等它就绪
        self._wait_readyok(timeout_sec=startup_timeout_sec)

    def _wait_readyok(self, timeout_sec: float) -> None:
        deadline = time.monotonic() + timeout_sec
        self._send("isready")
        while True:
            line = self._readline(deadline=deadline)
            if line is None:
                raise PikafishError("等待 readyok 超时")
            if line == "readyok":
                return

    def _send(self, cmd: str) -> None:
        if self._proc is None or self._proc.stdin is None:
            raise PikafishError("引擎未启动或已退出")
        try:
            self._proc.stdin.write(cmd + "\n")
            self._proc.stdin.flush()
        except (BrokenPipeError, OSError) as e:
            raise PikafishError(f"向引擎写入失败: {e}") from e

    def _readline(self, deadline: float) -> Optional[str]:
        """阻塞读一行；返回 None 表示进程已结束。

        Python subprocess 在 Windows 下不支持非阻塞 readline，这里用粗粒度
        deadline 检查：单次 readline 最多阻塞到引擎写入下一行；如果 deadline
        已过且 readline 又没立即返回，外层下一轮会发现并退出。
        """
        if self._proc is None or self._proc.stdout is None:
            return None
        if time.monotonic() > deadline:
            return None
        line = self._proc.stdout.readline()
        if line == "":
            # EOF：进程退出
            return None
        return line.rstrip("\r\n")


# ---------- 烟雾测试 ----------

def _smoke_test() -> None:
    """独立运行：python -m engine.pikafish

    打通通信、解析选项、跑一次 go movetime，并校验 bestmove 形态。
    """
    import config

    exe = config.PIKAFISH_DIR / config.PIKAFISH_EXE
    nnue = config.PIKAFISH_DIR / config.PIKAFISH_NNUE

    print(f"[smoke] exe : {exe}")
    print(f"[smoke] nnue: {nnue}")

    with PikafishEngine(
        exe_path=exe,
        nnue_path=nnue,
        threads=config.ENGINE_THREADS,
        hash_mb=config.ENGINE_HASH_MB,
        startup_timeout_sec=config.ENGINE_STARTUP_TIMEOUT_SEC,
    ) as eng:
        print(f"[smoke] options ({len(eng._available_options)}): "
              f"{sorted(eng._available_options)}")
        eng.new_game()

        fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
        move = eng.go(fen, movetime_ms=500)
        print(f"[smoke] bestmove: {move}")

        # 形态校验：4 个字符，列字母 a-i，行数字 0-9
        assert len(move) == 4, f"长度应为 4，实际: {move!r}"
        assert move[0] in "abcdefghi", f"列字母异常: {move!r}"
        assert move[1] in "0123456789", f"行数字异常: {move!r}"
        assert move[2] in "abcdefghi", f"列字母异常: {move!r}"
        assert move[3] in "0123456789", f"行数字异常: {move!r}"
        print("[smoke] 通信与走法格式校验通过")


if __name__ == "__main__":
    _smoke_test()
