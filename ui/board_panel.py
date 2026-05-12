"""象棋棋盘绘制 + 两步点击交互。

约定：
- 棋子画在交点上（与传统中国象棋一致）
- 第一次点击：选中己方棋子（高亮蓝框）
- 第二次点击：
    - 同色棋子 → 换选
    - 空格 / 敌方棋子 → 尝试走子，合法则 emit moveSelected
- 棋盘只负责"画"与"采集点击意图"，合法性校验仍由 rule.py 把守
- 不直接调用 Board.make_move，由 controller 走 executor 链路统一落子
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
)
from PySide6.QtWidgets import QWidget

import config
from core.board import Board
from core.constants import BLACK, BOARD_COLS, BOARD_ROWS, EMPTY, RED, piece_color
from core.pieces import PIECE_TO_CHINESE
from core.rule import is_legal_move


class BoardPanel(QWidget):
    """象棋棋盘视图。

    信号：
        moveSelected(from_row, from_col, to_row, to_col) — 玩家完成一次合法走子选择
    """

    moveSelected = Signal(int, int, int, int)
    illegalMoveTried = Signal(int, int, int, int)  # 玩家试图走一个非法走法，供 status bar 提示

    def __init__(self, board: Board, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.board = board
        self.setMinimumWidth(config.BOARD_PANEL_MIN_WIDTH)
        self.setMouseTracking(True)

        # 当前由谁来点击（玩家颜色）。由 controller 在回合切换时设置。
        self._player_color: int = RED

        self._input_enabled: bool = True
        self._selected: Optional[tuple[int, int]] = None  # 已选中的己方棋子
        self._hover_cell: Optional[tuple[int, int]] = None

    # ---------- 对外接口 ----------

    def set_board(self, board: Board) -> None:
        """重开时切换棋盘对象（也可对同一对象不变，仅 reset）。"""
        self.board = board
        self._selected = None
        self._hover_cell = None
        self.update()

    def set_input_enabled(self, enabled: bool) -> None:
        """AI 思考时禁用输入；玩家回合再启用。"""
        self._input_enabled = enabled
        if not enabled:
            self._selected = None
            self._hover_cell = None
        self.update()

    def set_player_color(self, color: int) -> None:
        """告诉面板"现在哪一方在点击"，用于第一次点击时校验棋子归属。"""
        self._player_color = color
        self._selected = None
        self.update()

    def clear_selection(self) -> None:
        self._selected = None
        self.update()

    # ---------- 几何 / 坐标转换 ----------

    def _metrics(self) -> tuple[float, float, float]:
        """返回 (cell_size, margin_x, margin_y)。

        棋盘有 BOARD_COLS-1=8 个水平间隔、BOARD_ROWS-1=9 个垂直间隔。
        取控件尺寸自适应：cell 取宽高约束的较小值，棋盘居中。
        """
        margin = config.BOARD_MARGIN
        w = self.width() - 2 * margin
        h = self.height() - 2 * margin
        cell = min(w / (BOARD_COLS - 1), h / (BOARD_ROWS - 1))
        board_w = cell * (BOARD_COLS - 1)
        board_h = cell * (BOARD_ROWS - 1)
        mx = (self.width() - board_w) / 2
        my = (self.height() - board_h) / 2
        return cell, mx, my

    def _cell_to_pixel(self, r: int, c: int) -> QPoint:
        cell, mx, my = self._metrics()
        return QPoint(int(mx + c * cell), int(my + r * cell))

    def _pixel_to_cell(self, x: float, y: float) -> Optional[tuple[int, int]]:
        cell, mx, my = self._metrics()
        if cell <= 0:
            return None
        c = round((x - mx) / cell)
        r = round((y - my) / cell)
        if 0 <= r < BOARD_ROWS and 0 <= c < BOARD_COLS:
            # 命中判定：距离最近交点不超过半格
            px, py = mx + c * cell, my + r * cell
            if abs(x - px) <= cell * 0.45 and abs(y - py) <= cell * 0.45:
                return (r, c)
        return None

    # ---------- 绘制 ----------

    def paintEvent(self, event: QPaintEvent) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)

        # 背景
        p.fillRect(self.rect(), QColor(*config.COLOR_BG))

        cell, mx, my = self._metrics()
        if cell <= 0:
            return

        pen = QPen(QColor(*config.COLOR_LINE))
        pen.setWidthF(max(1.0, cell * 0.035))
        p.setPen(pen)

        self._draw_grid(p, cell, mx, my)
        self._draw_palace_diagonals(p, cell, mx, my)
        self._draw_river_text(p, cell, mx, my)
        self._draw_position_marks(p, cell, mx, my)
        self._draw_last_move(p, cell, mx, my)
        self._draw_pieces(p, cell, mx, my)
        self._draw_selection(p, cell, mx, my)
        self._draw_hover(p, cell, mx, my)

    def _draw_grid(self, p: QPainter, cell: float, mx: float, my: float) -> None:
        """横线 10 条贯通；竖线 9 条但中间 7 条在河界处断开。"""
        # 横线 0..9
        for r in range(BOARD_ROWS):
            y = my + r * cell
            p.drawLine(int(mx), int(y), int(mx + (BOARD_COLS - 1) * cell), int(y))
        # 竖线：最左 col=0 和最右 col=8 整条贯通；中间 col=1..7 河界处断开
        river_top_y = my + 4 * cell
        river_bot_y = my + 5 * cell
        for c in range(BOARD_COLS):
            x = mx + c * cell
            if c == 0 or c == BOARD_COLS - 1:
                p.drawLine(int(x), int(my), int(x), int(my + (BOARD_ROWS - 1) * cell))
            else:
                p.drawLine(int(x), int(my), int(x), int(river_top_y))
                p.drawLine(int(x), int(river_bot_y), int(x), int(my + (BOARD_ROWS - 1) * cell))

    def _draw_palace_diagonals(self, p: QPainter, cell: float, mx: float, my: float) -> None:
        # 黑方九宫 (rows 0..2, cols 3..5)
        x3, x5 = mx + 3 * cell, mx + 5 * cell
        y0, y2 = my + 0 * cell, my + 2 * cell
        p.drawLine(int(x3), int(y0), int(x5), int(y2))
        p.drawLine(int(x5), int(y0), int(x3), int(y2))
        # 红方九宫 (rows 7..9, cols 3..5)
        y7, y9 = my + 7 * cell, my + 9 * cell
        p.drawLine(int(x3), int(y7), int(x5), int(y9))
        p.drawLine(int(x5), int(y7), int(x3), int(y9))

    def _draw_river_text(self, p: QPainter, cell: float, mx: float, my: float) -> None:
        font = QFont()
        font.setPointSizeF(max(10.0, cell * 0.45))
        font.setBold(True)
        p.setFont(font)
        p.setPen(QColor(*config.COLOR_LINE))
        # 楚河 在左侧（col 1..3 区域），汉界在右侧（col 5..7 区域）
        y_top = my + 4 * cell
        y_bot = my + 5 * cell
        left_rect = QRect(int(mx + 0.5 * cell), int(y_top), int(3 * cell), int(cell))
        right_rect = QRect(int(mx + 4.5 * cell), int(y_top), int(3 * cell), int(cell))
        p.drawText(left_rect, Qt.AlignCenter, "楚 河")
        p.drawText(right_rect, Qt.AlignCenter, "漢 界")

    def _draw_position_marks(self, p: QPainter, cell: float, mx: float, my: float) -> None:
        """画兵 / 炮位的"小十字"角标。兵卒位与炮位都按传统棋盘画。"""
        marks = [
            # 红方炮位（row=7, col=1, 7）；兵位（row=6, col=0,2,4,6,8）
            (7, 1), (7, 7),
            (6, 0), (6, 2), (6, 4), (6, 6), (6, 8),
            # 黑方炮位（row=2, col=1, 7）；卒位（row=3, col=0,2,4,6,8）
            (2, 1), (2, 7),
            (3, 0), (3, 2), (3, 4), (3, 6), (3, 8),
        ]
        arm = cell * 0.08
        gap = cell * 0.10
        pen = QPen(QColor(*config.COLOR_LINE))
        pen.setWidthF(max(1.0, cell * 0.025))
        p.setPen(pen)
        for r, c in marks:
            cx = mx + c * cell
            cy = my + r * cell
            # 四角"L"形
            for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
                # 边界处只画朝棋盘内的那两个角
                if c == 0 and sx == -1:
                    continue
                if c == BOARD_COLS - 1 and sx == 1:
                    continue
                x0 = cx + sx * gap
                y0 = cy + sy * gap
                p.drawLine(int(x0), int(y0), int(x0 + sx * arm), int(y0))
                p.drawLine(int(x0), int(y0), int(x0), int(y0 + sy * arm))

    def _draw_pieces(self, p: QPainter, cell: float, mx: float, my: float) -> None:
        radius = cell * 0.42
        font = QFont()
        font.setPointSizeF(max(10.0, cell * 0.42))
        font.setBold(True)
        p.setFont(font)

        for r in range(BOARD_ROWS):
            for c in range(BOARD_COLS):
                piece = self.board.cells[r][c]
                if piece == EMPTY:
                    continue
                cx = mx + c * cell
                cy = my + r * cell
                color = piece_color(piece)
                stroke = QColor(*config.COLOR_RED_PIECE) if color == RED else QColor(*config.COLOR_BLACK_PIECE)

                # 棋子底
                p.setBrush(QBrush(QColor(*config.COLOR_PIECE_FACE)))
                pen = QPen(stroke)
                pen.setWidthF(max(1.5, cell * 0.04))
                p.setPen(pen)
                p.drawEllipse(QPoint(int(cx), int(cy)), int(radius), int(radius))
                # 内圈装饰
                inner_pen = QPen(stroke)
                inner_pen.setWidthF(max(1.0, cell * 0.02))
                p.setPen(inner_pen)
                p.drawEllipse(QPoint(int(cx), int(cy)), int(radius * 0.82), int(radius * 0.82))

                # 文字
                p.setPen(stroke)
                p.drawText(
                    QRect(int(cx - radius), int(cy - radius), int(2 * radius), int(2 * radius)),
                    Qt.AlignCenter,
                    PIECE_TO_CHINESE[piece],
                )

    def _draw_last_move(self, p: QPainter, cell: float, mx: float, my: float) -> None:
        last = self.board.last_move
        if last is None:
            return
        pen = QPen(QColor(*config.COLOR_LAST_MOVE_MARK))
        pen.setWidthF(max(1.5, cell * 0.05))
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        side = cell * 0.85
        for r, c in ((last.from_row, last.from_col), (last.to_row, last.to_col)):
            cx = mx + c * cell
            cy = my + r * cell
            p.drawRect(QRect(int(cx - side / 2), int(cy - side / 2), int(side), int(side)))

    def _draw_selection(self, p: QPainter, cell: float, mx: float, my: float) -> None:
        if self._selected is None:
            return
        r, c = self._selected
        cx = mx + c * cell
        cy = my + r * cell
        pen = QPen(QColor(*config.COLOR_SELECTED_MARK))
        pen.setWidthF(max(2.0, cell * 0.07))
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        radius = cell * 0.45
        p.drawEllipse(QPoint(int(cx), int(cy)), int(radius), int(radius))

    def _draw_hover(self, p: QPainter, cell: float, mx: float, my: float) -> None:
        if self._hover_cell is None or not self._input_enabled:
            return
        r, c = self._hover_cell
        cx = mx + c * cell
        cy = my + r * cell
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(*config.COLOR_HOVER_MARK))
        radius = cell * 0.40
        p.drawEllipse(QPoint(int(cx), int(cy)), int(radius), int(radius))

    # ---------- 鼠标交互 ----------

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self._input_enabled:
            return
        pos = event.position()
        cell_rc = self._pixel_to_cell(pos.x(), pos.y())
        if cell_rc != self._hover_cell:
            self._hover_cell = cell_rc
            self.update()

    def leaveEvent(self, event) -> None:
        if self._hover_cell is not None:
            self._hover_cell = None
            self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.LeftButton:
            return
        if not self._input_enabled:
            return
        pos = event.position()
        cell_rc = self._pixel_to_cell(pos.x(), pos.y())
        if cell_rc is None:
            return

        r, c = cell_rc
        target_piece = self.board.cells[r][c]
        target_color = piece_color(target_piece)

        # 还没选中己方棋子：只能选自己的子
        if self._selected is None:
            if target_color == self._player_color:
                self._selected = (r, c)
                self.update()
            return

        # 已选中：再点己方任意子 → 改选
        if target_color == self._player_color:
            self._selected = (r, c)
            self.update()
            return

        # 已选中 → 点空 / 点敌子 → 尝试走子
        fr, fc = self._selected
        if is_legal_move(self.board, (fr, fc), (r, c)):
            self._selected = None
            self.update()
            self.moveSelected.emit(fr, fc, r, c)
        else:
            # 非法走法：保持选中状态，发信号给外层提示用户
            self.illegalMoveTried.emit(fr, fc, r, c)
