"""顶部状态栏：左侧文字 + 右侧「对局设置」「重新开始」按钮。"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget


class StatusBar(QWidget):
    """顶部状态栏。"""

    restartClicked = Signal()
    settingsClicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(40)
        self.setStyleSheet("background-color: #f4f1ea; border-bottom: 1px solid #ccc;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)

        self.label = QLabel("准备中…")
        self.label.setStyleSheet("font-size: 14pt; color: #222;")
        layout.addWidget(self.label, stretch=1)

        self.settings_btn = QPushButton("对局设置")
        self.settings_btn.setFixedWidth(100)
        self.settings_btn.clicked.connect(self.settingsClicked.emit)
        layout.addWidget(self.settings_btn)

        self.restart_btn = QPushButton("重新开始")
        self.restart_btn.setFixedWidth(100)
        self.restart_btn.clicked.connect(self.restartClicked.emit)
        layout.addWidget(self.restart_btn)

    def set_text(self, text: str) -> None:
        self.label.setText(text)
