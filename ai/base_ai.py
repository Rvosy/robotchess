"""AI 抽象接口。

与五子棋版的 BaseAI 有两点差异：
- 返回值从单点 (row, col) 扩展为 (from_rc, to_rc) 两点元组
- color 约定使用 core.constants 的 RED / BLACK（±1），不再是 1/2
"""

from __future__ import annotations

from core.board import Board


class BaseAI:
    """所有 AI 的公共接口。子类必须实现 get_move。"""

    def get_move(
        self, board: Board, color: int
    ) -> tuple[tuple[int, int], tuple[int, int]]:
        """根据当前棋盘和己方颜色，返回走子 (from_row, from_col), (to_row, to_col)。

        约定：
        - 返回值必须是合法走法（形状合规 + 走完不被将军），
          否则上层有权拒绝并报错。
        - AI 自身崩溃 / 超时 / 非法输出均抛异常，由上层处理。
        """
        raise NotImplementedError
