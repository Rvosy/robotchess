"""对局设置对话框。

承载新局开始前的玩家可调参数：
- 先手：玩家执红（先手）/ 玩家执黑（后手）
- 难度：简单 / 普通 / 困难 / 噩梦
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from ai.factory import (
    DIFFICULTY_EASY,
    DIFFICULTY_HARD,
    DIFFICULTY_NIGHTMARE,
    DIFFICULTY_NORMAL,
)
from core.constants import BLACK, RED


@dataclass
class GameSettings:
    """一局的玩家可调参数。

    human_color: 玩家执子颜色（RED=先手 / BLACK=后手）
    difficulty:  难度档位。默认 NORMAL
    """
    human_color: int = RED
    difficulty: str = DIFFICULTY_NORMAL


class SettingsDialog(QDialog):
    def __init__(self, current: GameSettings, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("对局设置")
        self.setModal(True)
        self.setMinimumWidth(320)

        layout = QVBoxLayout(self)

        # ---------- 先手 ----------
        first_group = QGroupBox("先手", self)
        first_layout = QVBoxLayout(first_group)
        self.rb_human_red = QRadioButton("玩家执红（先手）", first_group)
        self.rb_human_black = QRadioButton("玩家执黑（后手）", first_group)
        self._first_group = QButtonGroup(self)
        self._first_group.addButton(self.rb_human_red)
        self._first_group.addButton(self.rb_human_black)
        first_layout.addWidget(self.rb_human_red)
        first_layout.addWidget(self.rb_human_black)
        layout.addWidget(first_group)

        if current.human_color == BLACK:
            self.rb_human_black.setChecked(True)
        else:
            self.rb_human_red.setChecked(True)

        # ---------- 难度 ----------
        diff_group = QGroupBox("难度", self)
        diff_layout = QVBoxLayout(diff_group)
        self.rb_diff_easy = QRadioButton("简单", diff_group)
        self.rb_diff_normal = QRadioButton("普通", diff_group)
        self.rb_diff_hard = QRadioButton("困难", diff_group)
        self.rb_diff_nightmare = QRadioButton("噩梦", diff_group)
        self._diff_group = QButtonGroup(self)
        self._diff_group.addButton(self.rb_diff_easy)
        self._diff_group.addButton(self.rb_diff_normal)
        self._diff_group.addButton(self.rb_diff_hard)
        self._diff_group.addButton(self.rb_diff_nightmare)
        diff_layout.addWidget(self.rb_diff_easy)
        diff_layout.addWidget(self.rb_diff_normal)
        diff_layout.addWidget(self.rb_diff_hard)
        diff_layout.addWidget(self.rb_diff_nightmare)
        layout.addWidget(diff_group)

        if current.difficulty == DIFFICULTY_EASY:
            self.rb_diff_easy.setChecked(True)
        elif current.difficulty == DIFFICULTY_HARD:
            self.rb_diff_hard.setChecked(True)
        elif current.difficulty == DIFFICULTY_NIGHTMARE:
            self.rb_diff_nightmare.setChecked(True)
        else:
            self.rb_diff_normal.setChecked(True)

        # ---------- 确定 / 取消 ----------
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self
        )
        buttons.button(QDialogButtonBox.Ok).setText("确定")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_settings(self) -> GameSettings:
        human_color = BLACK if self.rb_human_black.isChecked() else RED
        if self.rb_diff_easy.isChecked():
            difficulty = DIFFICULTY_EASY
        elif self.rb_diff_hard.isChecked():
            difficulty = DIFFICULTY_HARD
        elif self.rb_diff_nightmare.isChecked():
            difficulty = DIFFICULTY_NIGHTMARE
        else:
            difficulty = DIFFICULTY_NORMAL
        return GameSettings(human_color=human_color, difficulty=difficulty)
