"""鼠标走子来源：把 BoardPanel 的点击信号转发为 InputSource.moveRequested。

GameController 看到的只是 InputSource 接口，无需知道走子来自鼠标还是摄像头。
"""

from __future__ import annotations

from typing import Optional

from core.board import Board
from ui.board_panel import BoardPanel

from .base_input import InputSource


class MouseInputSource(InputSource):
    """监听 BoardPanel.moveSelected，桥接为 InputSource.moveRequested。"""

    def __init__(self, board_panel: BoardPanel) -> None:
        super().__init__()
        self._panel = board_panel
        self._board: Optional[Board] = None
        self._panel.moveSelected.connect(self._on_panel_move)

    def start(self, board: Board) -> None:
        self._board = board
        self._panel.set_board(board)
        self._panel.set_input_enabled(True)

    def stop(self) -> None:
        self._panel.set_input_enabled(False)
        self._board = None

    def set_enabled(self, enabled: bool) -> None:
        self._panel.set_input_enabled(enabled)

    def set_player_color(self, color: int) -> None:
        """告诉 BoardPanel 当前由谁点击（己方棋子才能被选中）。"""
        self._panel.set_player_color(color)

    def _on_panel_move(self, fr: int, fc: int, tr: int, tc: int) -> None:
        # 走子合法性 BoardPanel 已经校验过；这里只做转发
        self.moveRequested.emit(fr, fc, tr, tc)
