"""把 PikafishEngine 包装为 BaseAI。

职责：
- FEN 序列化 → 喂给引擎
- bestmove 字符串解析 → (from_rc, to_rc)
- 不同难度档位下的 movetime / Skill Level 由 ai/factory 注入
"""

from __future__ import annotations

from ai.base_ai import BaseAI
from core.board import Board
from engine.pikafish import PikafishEngine, PikafishError


# UCI 列字母 → col
_FILE_TO_COL = {ch: i for i, ch in enumerate("abcdefghi")}


def parse_uci_move(uci: str) -> tuple[tuple[int, int], tuple[int, int]]:
    """解析 UCI 走法字符串如 "h2e2" → ((from_row, from_col), (to_row, to_col))。

    UCI 行号 0 = 红方底线 = 内部 row 9；映射 row = 9 - uci_rank。
    """
    if len(uci) != 4:
        raise ValueError(f"UCI 走法长度应为 4，实际 {uci!r}")
    fc = _FILE_TO_COL.get(uci[0])
    tc = _FILE_TO_COL.get(uci[2])
    if fc is None or tc is None:
        raise ValueError(f"UCI 列字母非法: {uci!r}")
    try:
        fr = 9 - int(uci[1])
        tr = 9 - int(uci[3])
    except ValueError as e:
        raise ValueError(f"UCI 行数字非法: {uci!r}") from e
    if not (0 <= fr <= 9 and 0 <= tr <= 9):
        raise ValueError(f"UCI 行越界: {uci!r}")
    return (fr, fc), (tr, tc)


def to_uci_move(from_rc: tuple[int, int], to_rc: tuple[int, int]) -> str:
    """逆向：内部坐标 → UCI 走法字符串。供调试 / 棋谱导出使用。"""
    files = "abcdefghi"
    fr, fc = from_rc
    tr, tc = to_rc
    return f"{files[fc]}{9 - fr}{files[tc]}{9 - tr}"


class PikafishAI(BaseAI):
    """同一引擎实例可被多个 PikafishAI 复用（每次 get_move 重置 Skill Level）。"""

    def __init__(
        self,
        engine: PikafishEngine,
        movetime_ms: int,
        skill_level: int | None = None,
    ) -> None:
        self.engine = engine
        self.movetime_ms = movetime_ms
        self.skill_level = skill_level

    def get_move(
        self, board: Board, color: int
    ) -> tuple[tuple[int, int], tuple[int, int]]:
        # 每次 get_move 前同步 Skill Level，难度切换无需重启引擎
        if self.skill_level is not None and self.engine.supports_option("Skill Level"):
            self.engine.set_option("Skill Level", str(self.skill_level))

        fen = board.to_fen()
        try:
            uci = self.engine.go(fen, self.movetime_ms)
        except PikafishError:
            raise  # 由上层 AIWorker 捕获并 emit failed

        return parse_uci_move(uci)


# ---------- 自测 ----------

def _self_test() -> None:
    """python -m ai.pikafish_ai 运行：仅验证坐标转换工具函数。"""
    # 红方开局炮二平五的 UCI 是 b2e2
    f, t = parse_uci_move("b2e2")
    assert f == (7, 1), f"b2 应为 (7,1)，实际 {f}"
    assert t == (7, 4), f"e2 应为 (7,4)，实际 {t}"
    print(f"[ok] b2e2 → {f} / {t}")

    # 黑方开局马八进七的 UCI 是 h9g7（对应 (0,7) → (2,6)）
    f, t = parse_uci_move("h9g7")
    assert f == (0, 7), f"h9 应为 (0,7)，实际 {f}"
    assert t == (2, 6), f"g7 应为 (2,6)，实际 {t}"
    print(f"[ok] h9g7 → {f} / {t}")

    # 往返一致
    assert to_uci_move((7, 1), (7, 4)) == "b2e2"
    assert to_uci_move((0, 7), (2, 6)) == "h9g7"
    print("[ok] to_uci_move 与 parse_uci_move 互逆")

    print("ai/pikafish_ai.py 自测全部通过")


if __name__ == "__main__":
    _self_test()
