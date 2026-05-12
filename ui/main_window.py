"""主窗口：状态栏 + 图像面板（左） + 棋盘面板（右）的组装。

只是组装容器，不持有游戏逻辑。GameController 通过：
- self.board_panel.moveSelected      玩家走子（rule.is_legal_move 已校验）
- self.status_bar.restartClicked     重开按钮信号
- self.status_bar.settingsClicked    设置按钮信号
- self.refresh()                     刷新棋盘渲染
- self.set_status(text)              更新状态栏文字
- self.image_panel                   第二版接 OpenCV 摄像头画面
- self.board_panel                   棋盘视图（也是 MouseInputSource 的来源）
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QSplitter, QVBoxLayout, QWidget

import config
from core.board import Board
from ui.board_panel import BoardPanel
from ui.image_panel import ImagePanel
from ui.status_bar import StatusBar


class MainWindow(QMainWindow):
    def __init__(self, board: Board, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("中国象棋（Pikafish 引擎）")
        self.resize(config.WINDOW_WIDTH, config.WINDOW_HEIGHT)

        self.board = board

        central = QWidget(self)
        self.setCentralWidget(central)
        v = QVBoxLayout(central)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # 顶部状态栏
        self.status_bar = StatusBar(self)
        v.addWidget(self.status_bar)

        # 主体：左右分屏
        splitter = QSplitter(Qt.Horizontal, self)
        self.image_panel = ImagePanel(splitter)
        self.board_panel = BoardPanel(board, splitter)
        splitter.addWidget(self.image_panel)
        splitter.addWidget(self.board_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([
            config.IMAGE_PANEL_MIN_WIDTH,
            config.WINDOW_WIDTH - config.IMAGE_PANEL_MIN_WIDTH,
        ])
        v.addWidget(splitter, stretch=1)

    # ---------- 公共接口 ----------

    def refresh(self) -> None:
        self.board_panel.update()

    def set_status(self, text: str) -> None:
        self.status_bar.set_text(text)
