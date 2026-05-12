"""棋盘 / 棋子核心常量。所有模块统一从这里读取。

坐标约定：
- (row, col)：row ∈ [0, 9] 从上到下；col ∈ [0, 8] 从左到右
- row=0 是黑方底线（FEN 第一行），row=9 是红方底线
- 与 Pikafish / FEN / UCI 一致，避免上下翻转踩坑
"""

# ---------- 棋盘尺寸 ----------
BOARD_ROWS = 10
BOARD_COLS = 9

# ---------- 阵营 ----------
EMPTY = 0
RED = 1      # 先手
BLACK = -1   # 后手

# ---------- 棋子类型（绝对值），方便区分阵营时直接用 sign ----------
KING = 1     # 将 / 帅
ADVISOR = 2  # 士 / 仕
BISHOP = 3   # 象 / 相
KNIGHT = 4   # 马
ROOK = 5     # 车
CANNON = 6   # 炮
PAWN = 7     # 兵 / 卒

# ---------- 带符号的棋子编码（Board.cells 直接存这个） ----------
# 红方（正数）
R_KING = RED * KING
R_ADVISOR = RED * ADVISOR
R_BISHOP = RED * BISHOP
R_KNIGHT = RED * KNIGHT
R_ROOK = RED * ROOK
R_CANNON = RED * CANNON
R_PAWN = RED * PAWN

# 黑方（负数）
B_KING = BLACK * KING
B_ADVISOR = BLACK * ADVISOR
B_BISHOP = BLACK * BISHOP
B_KNIGHT = BLACK * KNIGHT
B_ROOK = BLACK * ROOK
B_CANNON = BLACK * CANNON
B_PAWN = BLACK * PAWN


def piece_color(piece: int) -> int:
    """返回棋子颜色：RED / BLACK / EMPTY。"""
    if piece == EMPTY:
        return EMPTY
    return RED if piece > 0 else BLACK


def piece_type(piece: int) -> int:
    """返回棋子类型（KING..PAWN），EMPTY 返回 0。"""
    return abs(piece)


def opponent(color: int) -> int:
    """返回对手颜色。"""
    return BLACK if color == RED else RED
