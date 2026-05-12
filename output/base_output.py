"""走子执行抽象。

第一版：ScreenExecutor（同步刷新 BoardPanel，立即 emit moveExecuted）
第三版：RobotExecutor（机械臂物理落子 + 摄像头确认到位后才 emit moveExecuted）

GameController 等 moveExecuted 才进入下一回合，天然适配同步与异步两种模式。
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from core.board import Board, Move


class MoveExecutor(QObject):
    """走子执行抽象。

    信号：
        moveExecuted() — 走子完成，可以进入下一回合
        moveFailed(msg) — 物理执行失败（机械臂卡住 / 摄像头未确认到位等）

    约定：
        execute(move, board_after) 被调用时，board_after 已经是"落子后"的棋盘快照，
        executor 只负责"让这个状态真实落地"（屏幕刷新 / 机械臂操作）。
    """

    moveExecuted = Signal()
    moveFailed = Signal(str)

    def execute(self, move: Move, board_after: Board) -> None:
        raise NotImplementedError
