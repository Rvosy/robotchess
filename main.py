"""中国象棋（Pikafish 引擎版）主入口 + GameController。

游戏规则：
- 红方先手；玩家可在「对局设置」里选执红或执黑
- AI 决策完全由 Pikafish 子进程负责，启动时检查二进制 + NNUE 是否就位
- 引擎崩溃 / 超时 / 返回非法走法 → 弹窗报错并中止本局，不做兜底走法

线程模型：
- 玩家走子在主线程同步完成（点击 → executor 同步刷新 → 立即下一回合）
- AI 调用通过 AIWorker(QThread) 子线程执行，结果用信号回主线程
- ScreenExecutor 的 moveExecuted 信号统一驱动"进入下一回合"逻辑，
  这样第三版机械臂换上 RobotExecutor 后 controller 零改动

依赖关系：
    main.py
      ├─ engine.PikafishEngine        # 进程生命周期
      ├─ MainWindow                   # UI 组装
      ├─ MouseInputSource             # 玩家走子来源
      ├─ ScreenExecutor               # 走子落地
      └─ GameController               # 状态机
"""

from __future__ import annotations

import sys
from typing import Optional

from PySide6.QtWidgets import QApplication, QMessageBox

import config
from ai.base_ai import BaseAI
from ai.factory import (
    DIFFICULTY_LABEL,
    build_ai,
)
from core.board import Board
from core.constants import BLACK, RED, opponent
from core.rule import is_game_over, is_in_check, is_legal_move
from engine.pikafish import PikafishEngine, PikafishError
from input.mouse_input import MouseInputSource
from output.screen_output import ScreenExecutor
from ui.ai_worker import AIWorker
from ui.main_window import MainWindow
from ui.settings_dialog import GameSettings, SettingsDialog


def _color_name(color: int) -> str:
    return "红" if color == RED else "黑"


class GameController:
    """对局状态机：玩家 ↔ AI 轮换、判终局、重开、设置。"""

    def __init__(
        self,
        board: Board,
        window: MainWindow,
        engine: PikafishEngine,
    ) -> None:
        self.board = board
        self.window = window
        self.engine = engine

        self.settings = GameSettings()                  # 默认：玩家执红、普通
        self.ai: BaseAI = build_ai(self.settings.difficulty, engine)

        # IO 抽象层
        self.input_source = MouseInputSource(window.board_panel)
        self.executor = ScreenExecutor(window.board_panel)

        # AI 子线程
        self.worker: Optional[AIWorker] = None
        # 等待 executor.moveExecuted 后下一步的回调（执行完一步后切回合）
        self._post_execute_callable = None
        self.game_over = False

        # 信号连接
        self.input_source.moveRequested.connect(self.on_input_move_requested)
        self.executor.moveExecuted.connect(self.on_move_executed)
        self.executor.moveFailed.connect(self.on_executor_failed)
        window.board_panel.illegalMoveTried.connect(self.on_illegal_move)
        self.window.status_bar.restartClicked.connect(self.on_restart)
        self.window.status_bar.settingsClicked.connect(self.on_settings)

        self._begin_new_game()

    # ---------- 颜色辅助 ----------

    @property
    def human_color(self) -> int:
        return self.settings.human_color

    @property
    def ai_color(self) -> int:
        return opponent(self.settings.human_color)

    # ---------- 玩家分支 ----------

    def on_input_move_requested(self, fr: int, fc: int, tr: int, tc: int) -> None:
        """玩家通过 InputSource 提交了一次走子请求。"""
        if self.game_over or self.worker is not None:
            return
        if self.board.current_turn != self.human_color:
            return
        if not is_legal_move(self.board, (fr, fc), (tr, tc)):
            return

        # 写入数据层
        move = self.board.make_move((fr, fc), (tr, tc))
        # 设置走子完成后的下一步动作：检查终局并交给 AI
        self._post_execute_callable = self._after_human_executed
        self.executor.execute(move, self.board)

    def _after_human_executed(self) -> None:
        # 检查 AI 方是否已无路可走（被将死或困毙）
        if is_game_over(self.board, self.ai_color):
            if is_in_check(self.board, self.ai_color):
                msg = f"{_color_name(self.human_color)}方（你）将死对方，获胜！"
            else:
                msg = f"{_color_name(self.ai_color)}方无子可走（困毙），{_color_name(self.human_color)}方（你）获胜"
            self._end_game(msg)
            return
        self._start_ai_turn()

    # ---------- AI 分支 ----------

    def _start_ai_turn(self) -> None:
        self.input_source.set_enabled(False)
        check_hint = "（将军！）" if is_in_check(self.board, self.ai_color) else ""
        self.window.set_status(
            f"{_color_name(self.ai_color)}方回合（AI 思考中…）"
            f" · 难度: {DIFFICULTY_LABEL.get(self.settings.difficulty, '普通')}"
            f"{check_hint}"
        )

        # 每个新回合用一个全新 worker；engine 在 worker 子线程里被串行调用
        self.worker = AIWorker(self.ai, self.board, self.ai_color)
        self.worker.moveReady.connect(self.on_ai_move_ready)
        self.worker.failed.connect(self.on_ai_failed)
        self.worker.finished.connect(self._cleanup_worker)
        self.worker.start()

    def on_ai_move_ready(self, fr: int, fc: int, tr: int, tc: int) -> None:
        if self.game_over:
            return
        # 防御性校验：理论上 Pikafish 不会返回非法走法
        if not is_legal_move(self.board, (fr, fc), (tr, tc)):
            self._end_game(f"AI 返回非法走法 ({fr},{fc})→({tr},{tc})，对局中止")
            return

        move = self.board.make_move((fr, fc), (tr, tc))
        self._post_execute_callable = self._after_ai_executed
        self.executor.execute(move, self.board)

    def _after_ai_executed(self) -> None:
        if is_game_over(self.board, self.human_color):
            # 区分将死与困毙，给玩家更清晰的反馈
            if is_in_check(self.board, self.human_color):
                msg = f"{_color_name(self.ai_color)}方（AI）将死你了，获胜！"
            else:
                msg = f"{_color_name(self.human_color)}方无子可走（困毙），{_color_name(self.ai_color)}方（AI）获胜"
            self._end_game(msg)
            return
        self.input_source.set_enabled(True)
        self.input_source.set_player_color(self.human_color)
        self._set_human_turn_status()
        # 若被将军（但仍有应将走法）→ 弹窗提示，避免玩家以为程序卡住
        if is_in_check(self.board, self.human_color):
            QMessageBox.warning(
                self.window,
                "将军！",
                f"AI 将了你一军，必须应将（避将 / 垫将 / 吃将军子）。",
            )

    def on_ai_failed(self, msg: str) -> None:
        QMessageBox.critical(self.window, "引擎错误", f"Pikafish 返回错误：\n{msg}")
        self.game_over = True
        self.input_source.set_enabled(False)
        self.window.set_status(f"引擎错误：{msg} · 请重新开始")

    def _cleanup_worker(self) -> None:
        if self.worker is not None:
            self.worker.deleteLater()
            self.worker = None

    # ---------- Executor 完成回调 ----------

    def on_move_executed(self) -> None:
        """ScreenExecutor / RobotExecutor 完成一次走子后回调，决定下一步走谁。"""
        if self.game_over:
            return
        cb = self._post_execute_callable
        self._post_execute_callable = None
        if cb is not None:
            cb()

    def on_executor_failed(self, msg: str) -> None:
        """走子执行失败（机械臂卡住 / 摄像头未确认到位）—— 第一版不会触发。"""
        QMessageBox.critical(self.window, "执行错误", f"走子执行失败：\n{msg}")
        self.game_over = True
        self.input_source.set_enabled(False)
        self.window.set_status(f"执行错误：{msg} · 请重新开始")

    def on_illegal_move(self, fr: int, fc: int, tr: int, tc: int) -> None:
        """玩家试图走非法走法（含"走完仍被将军"）。在状态栏短暂提示原因。"""
        # 真正原因可能多种；最常见是被将军时不应将。直接拼提示，避免误导。
        if is_in_check(self.board, self.human_color):
            self.window.set_status(
                f"{_color_name(self.human_color)}方被将军！该走法不能解除将军，请重新选择"
            )
        else:
            self.window.set_status("该走法不合法，请重新选择")

    # ---------- 重开 / 设置 ----------

    def on_restart(self) -> None:
        if self.worker is not None:
            self.window.set_status("AI 思考中，无法重开，请稍候…")
            return
        self._begin_new_game()

    def on_settings(self) -> None:
        if self.worker is not None:
            self.window.set_status("AI 思考中，无法打开设置，请稍候…")
            return
        dlg = SettingsDialog(self.settings, parent=self.window)
        if dlg.exec() == SettingsDialog.Accepted:
            self.settings = dlg.get_settings()
            self._begin_new_game()

    # ---------- 内部 ----------

    def _begin_new_game(self) -> None:
        """按当前 settings 开新局：重建 AI、清盘、按先后手决定谁先动。"""
        self.ai = build_ai(self.settings.difficulty, self.engine)
        try:
            self.engine.new_game()
        except PikafishError as e:
            QMessageBox.critical(self.window, "引擎错误", f"重置引擎失败：\n{e}")
            self.game_over = True
            return

        self.board.reset()
        self.game_over = False
        self._post_execute_callable = None

        self.input_source.start(self.board)
        self.input_source.set_player_color(self.human_color)
        self.window.refresh()

        if self.board.current_turn == self.ai_color:
            # AI 先手（玩家执黑时）
            self._start_ai_turn()
        else:
            self.input_source.set_enabled(True)
            self._set_human_turn_status()

    def _set_human_turn_status(self) -> None:
        check_hint = "（将军！）" if is_in_check(self.board, self.human_color) else ""
        self.window.set_status(
            f"{_color_name(self.human_color)}方回合（你）"
            f" · 难度: {DIFFICULTY_LABEL.get(self.settings.difficulty, '普通')}"
            f"{check_hint}"
        )

    # ---------- 收尾 ----------

    def _end_game(self, message: str) -> None:
        self.game_over = True
        self.input_source.set_enabled(False)
        self.window.set_status(message + "  （点右上角「重新开始」开始新局）")
        QMessageBox.information(self.window, "对局结束", message)


# ---------- 启动 ----------

def _ensure_engine_files() -> tuple[bool, str]:
    """启动前自检 Pikafish 文件是否就位。"""
    exe = config.PIKAFISH_DIR / config.PIKAFISH_EXE
    nnue = config.PIKAFISH_DIR / config.PIKAFISH_NNUE
    missing = []
    if not exe.exists():
        missing.append(str(exe))
    if not nnue.exists():
        missing.append(str(nnue))
    if missing:
        return False, "以下 Pikafish 文件缺失：\n  " + "\n  ".join(missing)
    return True, ""


def main() -> int:
    app = QApplication(sys.argv)

    # 1. 自检引擎文件
    ok, msg = _ensure_engine_files()
    if not ok:
        QMessageBox.critical(None, "引擎文件缺失", msg)
        return 1

    # 2. 启动 Pikafish 子进程
    try:
        engine = PikafishEngine(
            exe_path=config.PIKAFISH_DIR / config.PIKAFISH_EXE,
            nnue_path=config.PIKAFISH_DIR / config.PIKAFISH_NNUE,
            threads=config.ENGINE_THREADS,
            hash_mb=config.ENGINE_HASH_MB,
            startup_timeout_sec=config.ENGINE_STARTUP_TIMEOUT_SEC,
        )
    except PikafishError as e:
        QMessageBox.critical(None, "引擎启动失败", f"无法启动 Pikafish：\n{e}")
        return 1

    # 3. 组装 UI 与 controller
    board = Board()
    window = MainWindow(board)
    controller = GameController(board, window, engine)
    window._controller = controller  # 防 GC

    # 退出时优雅关闭引擎子进程
    app.aboutToQuit.connect(engine.quit)

    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
