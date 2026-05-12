"""棋子字符与显示文字映射。

- FEN 字符：标准 K/A/B/N/R/C/P，红方大写、黑方小写
- 中文显示：将/帅、士/仕、象/相、马/傌、车/俥、炮/砲、卒/兵
  双方用不同字形主要为了视觉区分，第一版可保留传统写法
"""

from __future__ import annotations

from .constants import (
    B_ADVISOR,
    B_BISHOP,
    B_CANNON,
    B_KING,
    B_KNIGHT,
    B_PAWN,
    B_ROOK,
    EMPTY,
    R_ADVISOR,
    R_BISHOP,
    R_CANNON,
    R_KING,
    R_KNIGHT,
    R_PAWN,
    R_ROOK,
)


# 整数编码 → FEN 字符
PIECE_TO_FEN: dict[int, str] = {
    R_KING: "K",
    R_ADVISOR: "A",
    R_BISHOP: "B",
    R_KNIGHT: "N",
    R_ROOK: "R",
    R_CANNON: "C",
    R_PAWN: "P",
    B_KING: "k",
    B_ADVISOR: "a",
    B_BISHOP: "b",
    B_KNIGHT: "n",
    B_ROOK: "r",
    B_CANNON: "c",
    B_PAWN: "p",
}

# FEN 字符 → 整数编码
FEN_TO_PIECE: dict[str, int] = {v: k for k, v in PIECE_TO_FEN.items()}


# 整数编码 → 中文显示字
PIECE_TO_CHINESE: dict[int, str] = {
    R_KING: "帅",
    R_ADVISOR: "仕",
    R_BISHOP: "相",
    R_KNIGHT: "傌",
    R_ROOK: "俥",
    R_CANNON: "炮",
    R_PAWN: "兵",
    B_KING: "将",
    B_ADVISOR: "士",
    B_BISHOP: "象",
    B_KNIGHT: "马",
    B_ROOK: "车",
    B_CANNON: "砲",
    B_PAWN: "卒",
    EMPTY: "",
}
