"""AI 计算线程。

子线程执行 PikafishAI.get_move（内含同步等待引擎 bestmove），
结果通过 Qt 信号回主线程，避免阻塞 UI 事件循环。

board.copy() 是关键：子线程读棋盘期间，主线程绝对不能修改它。
（虽然第一版 controller 实际上是"AI 思考时禁用所有输入"，
 但拷贝拍快照是更稳妥的契约。）
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from ai.base_ai import BaseAI
from core.board import Board


class AIWorker(QThread):
    moveReady = Signal(int, int, int, int)   # from_row, from_col, to_row, to_col
    failed = Signal(str)

    def __init__(self, ai: BaseAI, board: Board, color: int, parent=None) -> None:
        super().__init__(parent)
        self.ai = ai
        self.board = board.copy()
        self.color = color

    def run(self) -> None:
        try:
            (fr, fc), (tr, tc) = self.ai.get_move(self.board, self.color)
            self.moveReady.emit(int(fr), int(fc), int(tr), int(tc))
        except Exception as e:
            self.failed.emit(f"{type(e).__name__}: {e}")
