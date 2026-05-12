"""屏幕走子执行器：第一版同步刷新 BoardPanel。

之所以仍走"异步信号链"而非直接同步落子，是为了让 controller 状态机与
第三版 RobotExecutor 共用同一套等待逻辑（机械臂物理落子必然异步）。
"""

from __future__ import annotations

from PySide6.QtCore import QTimer

from core.board import Board, Move
from ui.board_panel import BoardPanel

from .base_output import MoveExecutor


class ScreenExecutor(MoveExecutor):
    """同步刷新棋盘并通过 QTimer.singleShot(0) 排队 emit moveExecuted。

    使用 singleShot(0) 而非立即 emit，是为了：
    - 让信号在事件循环下一帧才到 controller，避免"走子 → 立即下一回合 → AIWorker 启动
      在 paintEvent 之前"造成 UI 跳过中间帧
    - 与第三版异步行为一致（emit 总是在当前调用栈之后）
    """

    def __init__(self, board_panel: BoardPanel) -> None:
        super().__init__()
        self._panel = board_panel

    def execute(self, move: Move, board_after: Board) -> None:
        # 棋盘数据已经由 controller 写入；这里只触发重绘
        self._panel.set_board(board_after)
        self._panel.update()
        QTimer.singleShot(0, self.moveExecuted.emit)
