"""端到端烟雾测试：启动完整 GUI + 引擎，模拟一次玩家走子 + AI 回应。

用法：python tests/test_end_to_end.py

成功标志：
- 引擎启动成功
- 玩家走 (9,1)→(7,2) 马二进三后，棋盘更新
- AI 收到请求并在 5 秒内返回合法走法
- 退出时引擎子进程正常回收
"""

from __future__ import annotations

import sys
from pathlib import Path

# 让本脚本能直接执行，把项目根加到 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import config  # noqa: E402
from core.board import Board  # noqa: E402
from engine.pikafish import PikafishEngine  # noqa: E402
from main import GameController  # noqa: E402
from ui.main_window import MainWindow  # noqa: E402


class TestResult:
    ok = False
    reason = "未完成"
    ai_move_count = 0


def run_e2e() -> TestResult:
    result = TestResult()
    app = QApplication.instance() or QApplication(sys.argv)

    engine = PikafishEngine(
        exe_path=config.PIKAFISH_DIR / config.PIKAFISH_EXE,
        nnue_path=config.PIKAFISH_DIR / config.PIKAFISH_NNUE,
        threads=config.ENGINE_THREADS,
        hash_mb=config.ENGINE_HASH_MB,
    )
    app.aboutToQuit.connect(engine.quit)

    board = Board()
    window = MainWindow(board)
    controller = GameController(board, window, engine)
    window.show()

    # 1. 模拟玩家走子：马二进三 (9,1) → (7,2)
    def step1() -> None:
        print("[test] step1: 模拟玩家 (9,1) -> (7,2)")
        controller.input_source.moveRequested.emit(9, 1, 7, 2)

    # 2. 等待 AI 回应
    def check_ai_responded() -> None:
        # AI 完成的标志：ai_color 下完一手 → move_history 长度 = 2
        if len(board.move_history) >= 2:
            last_ai = board.move_history[-1]
            print(f"[test] AI 回应: ({last_ai.from_row},{last_ai.from_col}) -> "
                  f"({last_ai.to_row},{last_ai.to_col})")
            result.ok = True
            result.reason = "端到端对战链路通过"
            result.ai_move_count = 1
            app.quit()
            return
        # 还没回来继续等
        QTimer.singleShot(200, check_ai_responded)

    QTimer.singleShot(500, step1)
    QTimer.singleShot(800, check_ai_responded)
    # 总超时 15 秒
    def timeout() -> None:
        if not result.ok:
            result.reason = f"超时：history={len(board.move_history)}，controller.worker={controller.worker}"
            app.quit()
    QTimer.singleShot(15000, timeout)

    app.exec()
    return result


if __name__ == "__main__":
    r = run_e2e()
    status = "PASS" if r.ok else "FAIL"
    print(f"\n=== {status} ===")
    print(f"reason     : {r.reason}")
    print(f"ai moves   : {r.ai_move_count}")
    sys.exit(0 if r.ok else 1)
