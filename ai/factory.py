"""AI 工厂：难度字符串 → BaseAI 实例。

难度档位由 ui.settings_dialog 定义为字符串常量，本工厂把它们映射到
PikafishAI 的 (movetime_ms, skill_level) 配置。
"""

from __future__ import annotations

from ai.base_ai import BaseAI
from ai.pikafish_ai import PikafishAI
from engine.pikafish import PikafishEngine


# 难度字符串常量（与 ui.settings_dialog 必须一致；放这里也避免 settings_dialog 反向 import）
DIFFICULTY_EASY = "easy"
DIFFICULTY_NORMAL = "normal"
DIFFICULTY_HARD = "hard"
DIFFICULTY_NIGHTMARE = "nightmare"

DIFFICULTY_LABEL = {
    DIFFICULTY_EASY: "简单",
    DIFFICULTY_NORMAL: "普通",
    DIFFICULTY_HARD: "困难",
    DIFFICULTY_NIGHTMARE: "噩梦",
}


# Pikafish Skill Level 范围 0..20。简单档额外启用 UCI 限强，避免最低 Skill 仍过强。
DIFFICULTY_PRESETS: dict[str, dict[str, int | bool | None]] = {
    DIFFICULTY_EASY: {
        "movetime_ms": 80,
        "skill_level": 0,
        "limit_strength": True,
        "uci_elo": 1320,
    },
    DIFFICULTY_NORMAL: {
        "movetime_ms": 500,
        "skill_level": 5,
        "limit_strength": False,
        "uci_elo": None,
    },
    DIFFICULTY_HARD: {
        "movetime_ms": 1500,
        "skill_level": 15,
        "limit_strength": False,
        "uci_elo": None,
    },
    DIFFICULTY_NIGHTMARE: {
        "movetime_ms": 3000,
        "skill_level": 20,
        "limit_strength": False,
        "uci_elo": None,
    },
}


def build_ai(difficulty: str, engine: PikafishEngine) -> BaseAI:
    """根据难度字符串返回 PikafishAI。未知档位回退到普通档。"""
    preset = DIFFICULTY_PRESETS.get(difficulty, DIFFICULTY_PRESETS[DIFFICULTY_NORMAL])
    return PikafishAI(
        engine=engine,
        movetime_ms=int(preset["movetime_ms"]),
        skill_level=int(preset["skill_level"]) if preset["skill_level"] is not None else None,
        limit_strength=bool(preset["limit_strength"]),
        uci_elo=int(preset["uci_elo"]) if preset["uci_elo"] is not None else None,
    )
