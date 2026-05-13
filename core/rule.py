"""中国象棋规则：走法合法性、将军检测、终局判定。

设计约定：
- 坐标系与 core.constants 保持一致（row 0=黑方底线，row 9=红方底线）
- 本模块只读 board.cells，不调用 board.make_move / undo_move（为避免污染 history）
- 所有函数都是纯函数式的合法性判断；搜索 / 评分不在此实现
"""

from __future__ import annotations

from .board import Board
from .constants import (
    ADVISOR,
    BISHOP,
    BLACK,
    BOARD_COLS,
    BOARD_ROWS,
    CANNON,
    EMPTY,
    KING,
    KNIGHT,
    PAWN,
    RED,
    ROOK,
    piece_color,
    piece_type,
)


# ---------- 九宫 ----------
PALACE_COLS = (3, 4, 5)
RED_PALACE_ROWS = (7, 8, 9)
BLACK_PALACE_ROWS = (0, 1, 2)


def _in_palace(r: int, c: int, color: int) -> bool:
    if c not in PALACE_COLS:
        return False
    if color == RED:
        return r in RED_PALACE_ROWS
    return r in BLACK_PALACE_ROWS


def _has_crossed_river(r: int, color: int) -> bool:
    """兵/卒是否已过河。红方过河后 row ≤ 4，黑方过河后 row ≥ 5。"""
    if color == RED:
        return r <= 4
    return r >= 5


# ---------- 各棋子伪合法走法（不考虑"走完后自己被将军"） ----------

def _king_ok(board: Board, fr: int, fc: int, tr: int, tc: int, color: int) -> bool:
    if not _in_palace(tr, tc, color):
        return False
    return abs(tr - fr) + abs(tc - fc) == 1


def _advisor_ok(board: Board, fr: int, fc: int, tr: int, tc: int, color: int) -> bool:
    if not _in_palace(tr, tc, color):
        return False
    return abs(tr - fr) == 1 and abs(tc - fc) == 1


def _bishop_ok(board: Board, fr: int, fc: int, tr: int, tc: int, color: int) -> bool:
    if abs(tr - fr) != 2 or abs(tc - fc) != 2:
        return False
    # 象不过河
    if color == RED and tr < 5:
        return False
    if color == BLACK and tr > 4:
        return False
    # 塞象眼：田字中心不能有子
    mid_r = (fr + tr) // 2
    mid_c = (fc + tc) // 2
    return board.cells[mid_r][mid_c] == EMPTY


def _knight_ok(board: Board, fr: int, fc: int, tr: int, tc: int, color: int) -> bool:
    dr = tr - fr
    dc = tc - fc
    if (abs(dr), abs(dc)) not in ((1, 2), (2, 1)):
        return False
    # 蹩马腿：沿"长边方向"紧邻起点的那一格
    if abs(dr) == 2:
        block_r = fr + (1 if dr > 0 else -1)
        block_c = fc
    else:
        block_r = fr
        block_c = fc + (1 if dc > 0 else -1)
    return board.cells[block_r][block_c] == EMPTY


def _rook_ok(board: Board, fr: int, fc: int, tr: int, tc: int, color: int) -> bool:
    if fr != tr and fc != tc:
        return False
    return _count_between(board, fr, fc, tr, tc) == 0


def _cannon_ok(board: Board, fr: int, fc: int, tr: int, tc: int, color: int) -> bool:
    if fr != tr and fc != tc:
        return False
    screens = _count_between(board, fr, fc, tr, tc)
    target = board.cells[tr][tc]
    if target == EMPTY:
        return screens == 0             # 平移：路径必须全空
    return screens == 1                 # 吃子：恰好一个炮架


def _pawn_ok(board: Board, fr: int, fc: int, tr: int, tc: int, color: int) -> bool:
    dr = tr - fr
    dc = tc - fc
    forward = -1 if color == RED else 1
    # 向前一步
    if dr == forward and dc == 0:
        return True
    # 过河后可横走一步
    if _has_crossed_river(fr, color) and dr == 0 and abs(dc) == 1:
        return True
    return False


_DISPATCH = {
    KING: _king_ok,
    ADVISOR: _advisor_ok,
    BISHOP: _bishop_ok,
    KNIGHT: _knight_ok,
    ROOK: _rook_ok,
    CANNON: _cannon_ok,
    PAWN: _pawn_ok,
}


def _count_between(board: Board, fr: int, fc: int, tr: int, tc: int) -> int:
    """同行或同列两点间的棋子数（不含端点）。非同行同列返回 0，调用方应先判方向。"""
    if fr == tr:
        step = 1 if tc > fc else -1
        count = 0
        c = fc + step
        while c != tc:
            if board.cells[fr][c] != EMPTY:
                count += 1
            c += step
        return count
    if fc == tc:
        step = 1 if tr > fr else -1
        count = 0
        r = fr + step
        while r != tr:
            if board.cells[r][fc] != EMPTY:
                count += 1
            r += step
        return count
    return 0


# ---------- 对外 API ----------

def is_pseudo_legal(board: Board, from_rc: tuple[int, int], to_rc: tuple[int, int]) -> bool:
    """伪合法：形状合规 + 不踩自己子，不管走完后是否被将军。"""
    fr, fc = from_rc
    tr, tc = to_rc
    if not (board.in_bounds(fr, fc) and board.in_bounds(tr, tc)):
        return False
    if (fr, fc) == (tr, tc):
        return False
    piece = board.cells[fr][fc]
    if piece == EMPTY:
        return False
    color = piece_color(piece)
    target = board.cells[tr][tc]
    if target != EMPTY and piece_color(target) == color:
        return False
    handler = _DISPATCH.get(piece_type(piece))
    if handler is None:
        return False
    return handler(board, fr, fc, tr, tc, color)


def kings_facing(board: Board) -> bool:
    """飞将：两王同列且中间无子。"""
    rk = board.find_king(RED)
    bk = board.find_king(BLACK)
    if rk is None or bk is None:
        return False
    if rk[1] != bk[1]:
        return False
    return _count_between(board, rk[0], rk[1], bk[0], bk[1]) == 0


def is_in_check(board: Board, color: int) -> bool:
    """color 方当前是否被将军（含飞将）。"""
    return len(find_checkers(board, color)) > 0


def find_checkers(board: Board, color: int) -> list[tuple[int, int]]:
    """返回所有正在将军 color 方将/帅的对方棋子坐标。

    飞将也视为由对方将/帅造成将军，返回对方将/帅坐标。
    """
    king = board.find_king(color)
    if king is None:
        return []

    checkers: list[tuple[int, int]] = []
    if kings_facing(board):
        enemy_king = board.find_king(BLACK if color == RED else RED)
        if enemy_king is not None:
            checkers.append(enemy_king)

    for r in range(BOARD_ROWS):
        for c in range(BOARD_COLS):
            p = board.cells[r][c]
            if p == EMPTY or piece_color(p) == color:
                continue
            if is_pseudo_legal(board, (r, c), king):
                checkers.append((r, c))
    return checkers


def find_checkers_after_move(
    board: Board,
    color: int,
    from_rc: tuple[int, int],
    to_rc: tuple[int, int],
) -> list[tuple[int, int]]:
    """试走一步后，返回 color 方仍被哪些棋子将军。

    仅用于 UI 提示应将失败原因；函数会原样回滚棋盘，不污染走子历史。
    伪非法走法没有明确的"试走后局面"，返回空列表。
    """
    if not is_pseudo_legal(board, from_rc, to_rc):
        return []

    fr, fc = from_rc
    tr, tc = to_rc
    saved_from = board.cells[fr][fc]
    saved_to = board.cells[tr][tc]
    board.cells[tr][tc] = saved_from
    board.cells[fr][fc] = EMPTY
    try:
        return find_checkers(board, color)
    finally:
        board.cells[fr][fc] = saved_from
        board.cells[tr][tc] = saved_to


def is_legal_move(board: Board, from_rc: tuple[int, int], to_rc: tuple[int, int]) -> bool:
    """完整合法性：伪合法 + 走完后己方不被将军。

    实现：直接修改 cells 试走、判定、原样回滚。不走 make_move 以免污染 history。
    """
    if not is_pseudo_legal(board, from_rc, to_rc):
        return False
    fr, fc = from_rc
    tr, tc = to_rc
    color = piece_color(board.cells[fr][fc])

    saved_from = board.cells[fr][fc]
    saved_to = board.cells[tr][tc]
    board.cells[tr][tc] = saved_from
    board.cells[fr][fc] = EMPTY
    try:
        return not is_in_check(board, color)
    finally:
        board.cells[fr][fc] = saved_from
        board.cells[tr][tc] = saved_to


def generate_legal_moves(
    board: Board, color: int
) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    """列出 color 方所有合法走法。用于终局判定，主对弈不依赖这个（AI 是 Pikafish）。"""
    moves: list[tuple[tuple[int, int], tuple[int, int]]] = []
    for fr in range(BOARD_ROWS):
        for fc in range(BOARD_COLS):
            p = board.cells[fr][fc]
            if p == EMPTY or piece_color(p) != color:
                continue
            for tr in range(BOARD_ROWS):
                for tc in range(BOARD_COLS):
                    if is_legal_move(board, (fr, fc), (tr, tc)):
                        moves.append(((fr, fc), (tr, tc)))
    return moves


def is_checkmate(board: Board, color: int) -> bool:
    """被将死：被将军且无任何合法走法。"""
    if not is_in_check(board, color):
        return False
    return len(generate_legal_moves(board, color)) == 0


def is_stalemate(board: Board, color: int) -> bool:
    """困毙：未被将军但无合法走法。象棋规则下同样判负。"""
    if is_in_check(board, color):
        return False
    return len(generate_legal_moves(board, color)) == 0


def is_game_over(board: Board, color: int) -> bool:
    """color 方是否无子可走（被将死或困毙）。象棋规则下均视为该方负。"""
    return len(generate_legal_moves(board, color)) == 0


# ---------- 自测 ----------

def _self_test() -> None:
    """python -m core.rule 运行"""
    from .constants import (
        B_CANNON,
        B_KING,
        B_KNIGHT,
        R_CANNON,
        R_KING,
        R_KNIGHT,
        R_PAWN,
    )

    # 1. 开局不被将军
    b = Board()
    assert not is_in_check(b, RED)
    assert not is_in_check(b, BLACK)
    print("[ok] 开局双方均不被将军")

    # 2. 开局合法走法数 = 44（红方），中国象棋开局合法走法标准值
    red_moves = generate_legal_moves(b, RED)
    print(f"[ok] 红方开局合法走法数: {len(red_moves)}")
    assert len(red_moves) == 44, f"期望 44，实际 {len(red_moves)}"
    black_moves = generate_legal_moves(b, BLACK)
    assert len(black_moves) == 44, f"黑方期望 44（对称），实际 {len(black_moves)}"
    print(f"[ok] 黑方开局合法走法数: {len(black_moves)}")

    # 3. 炮二平五 合法，仕六进五 合法，兵三进一 合法，过河兵横走非法
    assert is_legal_move(b, (7, 1), (7, 4)), "炮二平五应合法"
    assert is_legal_move(b, (9, 5), (8, 4)), "仕六进五应合法"
    # 兵三进一：红兵从 (6,2) → (5,2)
    assert is_legal_move(b, (6, 2), (5, 2)), "兵三进一应合法"
    # 未过河的兵不能横走
    assert not is_legal_move(b, (6, 2), (6, 1)), "未过河兵不能横走"
    print("[ok] 炮/士/兵 基础走法正确")

    # 4. 马蹩腿
    # 红马 (9,1)，若把 (8,1) 放一个己方子，(9,1)→(7,0) 应非法
    b2 = Board()
    b2.cells[8][1] = R_PAWN  # 临时塞一个兵蹩腿
    assert not is_legal_move(b2, (9, 1), (7, 0)), "马应被蹩腿"
    print("[ok] 马蹩腿检测正确")

    # 5. 象塞象眼
    b3 = Board()
    # 红象 (9,2) → (7,0)，象眼 (8,1) 初始为空，合法
    assert is_legal_move(b3, (9, 2), (7, 0)), "象眼空时象走田应合法"
    # 在象眼 (8,1) 放一个红兵堵象眼 → 非法
    b3.cells[8][1] = R_PAWN
    assert not is_legal_move(b3, (9, 2), (7, 0)), "象眼有子时应被塞住"
    print("[ok] 象塞象眼检测正确")

    # 6. 象不过河
    # 注意：摆残局测试时双方将帅必须不在同列，否则飞将让局面本身被将军
    b6 = Board.from_fen("3k5/9/2b6/9/9/9/9/9/9/4K4 b - - 0 1")
    # 黑象在 (2,2) → (4,0)：tr=4，仍属黑方半区（0-4），合法
    assert is_legal_move(b6, (2, 2), (4, 0)), "黑象走本方半区应合法"
    # 真的过河：用 (4, 2) → (6, 0)，tr=6 已进入红方半区
    b7 = Board.from_fen("3k5/9/9/9/2b6/9/9/9/9/4K4 b - - 0 1")
    assert not is_legal_move(b7, (4, 2), (6, 0)), "黑象过河应非法"
    print("[ok] 象不过河检测正确")

    # 7. 炮：隔山打子 vs 无炮架平移
    b8 = Board()
    # 红炮 (7,1) 平吃到 (7,2)：路径无棋，但 (7,2) 是空，属平移，count=0 合法
    assert is_legal_move(b8, (7, 1), (7, 2)), "炮平移到空格合法"
    # 红炮 (7,1) 吃黑炮 (2,1)：中间无子，count=0，吃子要 count=1，非法
    assert not is_legal_move(b8, (7, 1), (2, 1)), "炮无炮架不能吃"
    # 红炮 (7,1) 吃黑马 (0,1)：路径上有黑炮(2,1)一个，count=1，合法
    assert is_legal_move(b8, (7, 1), (0, 1)), "炮隔山打子（吃黑马）合法"
    print("[ok] 炮吃子 / 平移 规则正确")

    # 8. 飞将：两王同列且中间无子 → 非法局面；因此红帅若主动离开导致两王对脸也非法
    b9 = Board.from_fen("4k4/9/9/9/9/9/9/9/9/4K4 w - - 0 1")
    # 此时两王已经对脸，kings_facing = True
    assert kings_facing(b9), "初始两王同列无子应飞将"
    # 红帅 (9,4) → (9,3) 离开，不再同列，合法
    assert is_legal_move(b9, (9, 4), (9, 3)), "红帅离开同列应合法"
    # 红帅 (9,4) → (8,4)：仍同列，中间空，飞将，应非法
    assert not is_legal_move(b9, (9, 4), (8, 4)), "红帅走到仍与黑将对脸的位置应非法"
    print("[ok] 飞将规则正确")

    # 9. 自将过滤：红将帅旁边挂着一辆黑车，红帅前进会被将军，非法
    b10 = Board.from_fen("4k4/9/9/9/9/9/9/9/4r4/4K4 w - - 0 1")
    # 此时黑车在 (8,4) 直接将军红帅 (9,4)
    assert is_in_check(b10, RED), "此局面红方应被将军"
    assert find_checkers(b10, RED) == [(8, 4)], "应定位到黑车正在将军"
    # 红帅走 (9,3) 是否逃将？(9,3)→ 黑车沿列攻击 col 4，不到 col 3，安全
    assert is_legal_move(b10, (9, 4), (9, 3)), "红帅横向躲将合法"
    # 红帅 (9,4) → (9,5) 也能躲
    assert is_legal_move(b10, (9, 4), (9, 5)), "红帅另一侧躲将合法"
    # 但原地不动等候子？不是走法，不用测
    print("[ok] 自将过滤 / 将军判定正确")

    # 10. 将死：红帅被困
    #   黑车 (9,0) 横将红帅在 (9,4)，红帅两侧被士堵住，无法逃
    b11 = Board.from_fen("4k4/9/9/9/9/9/9/9/9/r2AKA3 w - - 0 1")
    # 红帅 (9,4)，被黑车 (9,0) 沿行攻击，两侧 (9,3)(9,5) 是自己的士堵住
    # 红帅 (9,4) → (8,4)：(8,4) 无子，黑车攻不到 col 4（车在 row 9），逃将成功
    # 所以这局面不是杀棋。构造真正杀棋：
    b12 = Board.from_fen("4k4/9/9/9/9/9/9/4r4/9/r3K4 w - - 0 1")
    # 红帅 (9,4)，黑车 (9,0) 横将；黑车 (7,4) 纵将。红帅逃哪都不行：
    #   (9,3)(9,5) 仍被 (9,0) 车攻 → 不行
    #   (8,4) 被 (7,4) 车攻 → 不行
    #   (8,3)(8,5) 不属于帅的走法（帅只走一格正交）
    # 没别的子能挡能吃
    assert is_checkmate(b12, RED), "该局面红方应被将死"
    assert find_checkers(b12, RED) == [(7, 4), (9, 0)], "双将时应返回全部将军来源"
    before_fen = b12.to_fen()
    assert find_checkers_after_move(b12, RED, (9, 4), (8, 4)) == [(7, 4)], "试走后应定位新的将军来源"
    assert b12.to_fen() == before_fen, "试走定位将军来源后必须回滚棋盘"
    print("[ok] 将死判定正确")

    # 11. 飞将来源定位：两王同列无子，互相造成将军
    b13 = Board.from_fen("4k4/9/9/9/9/9/9/9/9/4K4 w - - 0 1")
    assert find_checkers(b13, RED) == [(0, 4)], "飞将时红方应被黑将将军"
    assert find_checkers(b13, BLACK) == [(9, 4)], "飞将时黑方应被红帅将军"
    print("[ok] 将军来源定位正确")

    print("core/rule.py 自测全部通过")


if __name__ == "__main__":
    _self_test()
