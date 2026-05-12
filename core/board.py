"""棋盘数据结构。封装 10×9 二维数组 + 当前轮次 + 走子历史 + FEN 序列化。

设计要点：
- cells[row][col] 直接存带符号整数（见 constants.py），无需查 dict
- 不做合法性校验，由 rule.py 负责；本层是纯数据容器
- to_fen / from_fen 保证与 Pikafish UCI 通信无损
- diff 方法供未来 OpenCV 识别后做"内部棋盘 vs 镜头棋盘"对比
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .constants import (
    BLACK,
    BOARD_COLS,
    BOARD_ROWS,
    EMPTY,
    RED,
    piece_color,
)
from .pieces import FEN_TO_PIECE, PIECE_TO_FEN


@dataclass(frozen=True)
class Move:
    """一次走子的不可变记录。

    captured 表示被吃的棋子（EMPTY 表示未吃子），用于悔棋还原。
    """
    from_row: int
    from_col: int
    to_row: int
    to_col: int
    piece: int            # 走子的棋子（带符号）
    captured: int = EMPTY  # 终点位置原本的棋子


@dataclass(frozen=True)
class CellChange:
    """棋盘单格差异：用于 OpenCV 识别后对比内部棋盘与镜头棋盘。"""
    row: int
    col: int
    before: int
    after: int


class Board:
    """中国象棋棋盘 10 行 × 9 列。

    内部 self.cells: list[list[int]]，行优先存储；
    self.current_turn 记录"当前轮到哪方走"，初始为 RED。
    """

    INITIAL_FEN = (
        "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
    )

    def __init__(self) -> None:
        self.cells: list[list[int]] = [[EMPTY] * BOARD_COLS for _ in range(BOARD_ROWS)]
        self.current_turn: int = RED
        self.last_move: Optional[Move] = None
        self.move_history: list[Move] = []  # 仅记录走子（不含悔棋后的撤销）
        self.halfmove_clock: int = 0        # 距离上一次吃子或兵卒动的步数
        self.fullmove_number: int = 1       # 全回合数（每黑方走完 +1）
        self.reset()

    # ---------- 读写 ----------

    def get(self, r: int, c: int) -> int:
        return self.cells[r][c]

    def set_cell(self, r: int, c: int, piece: int) -> None:
        """直接写格子；不更新历史，仅用于构造局面或测试。"""
        self.cells[r][c] = piece

    def is_empty(self, r: int, c: int) -> bool:
        return self.cells[r][c] == EMPTY

    def in_bounds(self, r: int, c: int) -> bool:
        return 0 <= r < BOARD_ROWS and 0 <= c < BOARD_COLS

    # ---------- 走子 ----------

    def make_move(self, from_rc: tuple[int, int], to_rc: tuple[int, int]) -> Move:
        """执行走子，记录历史。**不做合法性校验**，由调用方先用 rule.is_legal_move。

        返回 Move 对象，包含被吃棋子，供悔棋还原使用。
        """
        fr, fc = from_rc
        tr, tc = to_rc
        piece = self.cells[fr][fc]
        captured = self.cells[tr][tc]

        self.cells[tr][tc] = piece
        self.cells[fr][fc] = EMPTY

        move = Move(fr, fc, tr, tc, piece, captured)
        self.last_move = move
        self.move_history.append(move)

        # FEN 计数：兵卒动或吃子归零，否则 +1
        from .constants import PAWN, piece_type
        if captured != EMPTY or piece_type(piece) == PAWN:
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1

        # 黑方走完后回合数 +1
        if self.current_turn == BLACK:
            self.fullmove_number += 1

        self.current_turn = -self.current_turn  # RED ↔ BLACK
        return move

    def undo_move(self) -> Optional[Move]:
        """悔最后一手。无历史可悔返回 None。

        仅用于规则模拟（rule.py 试走后回退）和未来的"撤销"按钮。
        """
        if not self.move_history:
            return None
        move = self.move_history.pop()
        self.cells[move.from_row][move.from_col] = move.piece
        self.cells[move.to_row][move.to_col] = move.captured

        if self.current_turn == RED:
            # 撤销的是黑方刚走的那一步
            self.fullmove_number = max(1, self.fullmove_number - 1)
        self.current_turn = -self.current_turn

        # halfmove_clock 严格还原需要更复杂的栈；第一版仅近似回退一步
        # （规则用试走/回退时不依赖 halfmove_clock，不影响合法性判定）
        self.halfmove_clock = max(0, self.halfmove_clock - 1)

        self.last_move = self.move_history[-1] if self.move_history else None
        return move

    # ---------- 工具 ----------

    def copy(self) -> "Board":
        """深拷贝。AIWorker 在子线程使用副本，避免与主线程数据竞争。"""
        new = Board.__new__(Board)
        new.cells = [row[:] for row in self.cells]
        new.current_turn = self.current_turn
        new.last_move = self.last_move
        new.move_history = list(self.move_history)
        new.halfmove_clock = self.halfmove_clock
        new.fullmove_number = self.fullmove_number
        return new

    def reset(self) -> None:
        """重置为初始局面。"""
        self._load_position_from_fen(self.INITIAL_FEN)
        self.last_move = None
        self.move_history = []

    def find_king(self, color: int) -> Optional[tuple[int, int]]:
        """找到指定方将/帅的位置。理论上一定存在；返回 None 仅在测试残局或非法局面时。"""
        from .constants import KING, piece_type
        for r in range(BOARD_ROWS):
            for c in range(BOARD_COLS):
                p = self.cells[r][c]
                if p != EMPTY and piece_type(p) == KING and piece_color(p) == color:
                    return (r, c)
        return None

    def diff(self, other: "Board") -> list[CellChange]:
        """对比两个棋盘，返回所有不同的格子。

        用于未来 OpenCV 识别：把识别出的棋盘与内部棋盘 diff，
        正常情况下应该恰好 2 格变化（一空一动）或 1 格变化（吃子）。
        """
        changes: list[CellChange] = []
        for r in range(BOARD_ROWS):
            for c in range(BOARD_COLS):
                a = self.cells[r][c]
                b = other.cells[r][c]
                if a != b:
                    changes.append(CellChange(r, c, a, b))
        return changes

    # ---------- FEN ----------

    def to_fen(self) -> str:
        """导出当前局面 FEN（含轮次 / 步数）。可直接喂给 Pikafish 的 position fen。"""
        rows: list[str] = []
        for r in range(BOARD_ROWS):
            buf = []
            empty_run = 0
            for c in range(BOARD_COLS):
                p = self.cells[r][c]
                if p == EMPTY:
                    empty_run += 1
                else:
                    if empty_run > 0:
                        buf.append(str(empty_run))
                        empty_run = 0
                    buf.append(PIECE_TO_FEN[p])
            if empty_run > 0:
                buf.append(str(empty_run))
            rows.append("".join(buf))

        side = "w" if self.current_turn == RED else "b"
        return f"{'/'.join(rows)} {side} - - {self.halfmove_clock} {self.fullmove_number}"

    @classmethod
    def from_fen(cls, fen: str) -> "Board":
        """从 FEN 构造棋盘。"""
        b = cls()
        b._load_position_from_fen(fen)
        b.last_move = None
        b.move_history = []
        return b

    def _load_position_from_fen(self, fen: str) -> None:
        """内部：解析 FEN 写入 cells / current_turn / 计数器。"""
        parts = fen.split()
        if len(parts) < 1:
            raise ValueError(f"FEN 字符串为空: {fen!r}")
        placement = parts[0]
        ranks = placement.split("/")
        if len(ranks) != BOARD_ROWS:
            raise ValueError(f"FEN 行数应为 {BOARD_ROWS}，实际 {len(ranks)}: {fen!r}")

        # 先清空，避免 from_fen 时残留上一次初始化的棋子
        for r in range(BOARD_ROWS):
            for c in range(BOARD_COLS):
                self.cells[r][c] = EMPTY

        for r, rank in enumerate(ranks):
            c = 0
            for ch in rank:
                if ch.isdigit():
                    c += int(ch)
                else:
                    if ch not in FEN_TO_PIECE:
                        raise ValueError(f"FEN 中存在未知字符 {ch!r}: {fen!r}")
                    if c >= BOARD_COLS:
                        raise ValueError(f"FEN 第 {r} 行超出 {BOARD_COLS} 列: {rank!r}")
                    self.cells[r][c] = FEN_TO_PIECE[ch]
                    c += 1
            if c != BOARD_COLS:
                raise ValueError(f"FEN 第 {r} 行列数应为 {BOARD_COLS}，实际 {c}: {rank!r}")

        side = parts[1] if len(parts) >= 2 else "w"
        self.current_turn = RED if side == "w" else BLACK

        try:
            self.halfmove_clock = int(parts[4]) if len(parts) >= 5 else 0
            self.fullmove_number = int(parts[5]) if len(parts) >= 6 else 1
        except ValueError:
            self.halfmove_clock = 0
            self.fullmove_number = 1


# ---------- 自测 ----------

def _self_test() -> None:
    """python -m core.board 运行：校验初始 FEN 往返、走子、悔棋、diff。"""
    b = Board()
    fen = b.to_fen()
    assert fen == Board.INITIAL_FEN, f"初始 FEN 不匹配:\n  {fen}\n  {Board.INITIAL_FEN}"
    print(f"[ok] 初始 FEN 正确: {fen}")

    # 走一手：红方炮二平五 b2 → e2（UCI 坐标），即 (row=7, col=1) → (row=7, col=4)
    move = b.make_move((7, 1), (7, 4))
    print(f"[ok] 走子: {move}")
    assert b.current_turn == BLACK
    assert b.cells[7][1] == EMPTY
    assert b.cells[7][4] != EMPTY

    # 悔棋还原
    b.undo_move()
    assert b.to_fen() == Board.INITIAL_FEN, "悔棋后局面应回到初始"
    print("[ok] 悔棋还原成功")

    # 拷贝隔离
    snap = b.copy()
    snap.make_move((7, 1), (7, 4))
    assert b.to_fen() == Board.INITIAL_FEN, "原盘不应被副本影响"
    assert snap.to_fen() != Board.INITIAL_FEN
    print("[ok] copy 隔离正确")

    # diff
    diffs = b.diff(snap)
    assert len(diffs) == 2, f"应恰好 2 处不同（起点+终点），实际 {len(diffs)}"
    print(f"[ok] diff 正确: {diffs}")

    # FEN 往返
    b2 = Board.from_fen("rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR b - - 5 10")
    assert b2.current_turn == BLACK
    assert b2.halfmove_clock == 5
    assert b2.fullmove_number == 10
    print(f"[ok] 自定义 FEN 解析: turn={b2.current_turn}, half={b2.halfmove_clock}, full={b2.fullmove_number}")

    print("core/board.py 自测全部通过")


if __name__ == "__main__":
    _self_test()
