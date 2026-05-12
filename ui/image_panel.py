"""左侧图像面板 —— 第一版占位 / 第二版接 OpenCV 摄像头画面。

第一版：
- 深灰背景 + 居中提示文字
- set_frame / set_recognized_board 方法已就位但暂不显示

第二版：
- set_frame(qimage) 接收 OpenCV 抓帧 → 等比缩放贴 QLabel
- set_recognized_board(board) 把识别结果叠加到当前帧上（红框标识识别到的棋子）
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPaintEvent, QPixmap
from PySide6.QtWidgets import QWidget

import config
from core.board import Board


class ImagePanel(QWidget):
    """图像 / 摄像头显示面板。"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(config.IMAGE_PANEL_MIN_WIDTH)

        self._frame: Optional[QPixmap] = None
        self._recognized_board: Optional[Board] = None

    # ---------- 对外接口（第二版填充逻辑） ----------

    def set_frame(self, image: QImage) -> None:
        """接收一帧摄像头画面。第二版由 CameraInputSource 调用。"""
        self._frame = QPixmap.fromImage(image)
        self.update()

    def set_recognized_board(self, board: Optional[Board]) -> None:
        """接收一次识别结果用于在画面上叠加可视化。第二版调用。"""
        self._recognized_board = board
        self.update()

    def clear(self) -> None:
        self._frame = None
        self._recognized_board = None
        self.update()

    # ---------- 绘制 ----------

    def paintEvent(self, event: QPaintEvent) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        # 深灰背景
        p.fillRect(self.rect(), QColor(45, 45, 50))

        if self._frame is not None and not self._frame.isNull():
            scaled = self._frame.scaled(
                self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            p.drawPixmap(x, y, scaled)
            # TODO(第二版): 若 self._recognized_board 非空，在画面上叠加识别框
            return

        # 占位提示
        p.setPen(QColor(180, 180, 180))
        font = QFont()
        font.setPointSize(14)
        p.setFont(font)
        p.drawText(
            self.rect(),
            Qt.AlignCenter,
            "摄像头未启用\n（第二版接入 OpenCV 后\n这里会显示实时画面）",
        )
