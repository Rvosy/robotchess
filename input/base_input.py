"""走子来源抽象。

第一版：MouseInputSource（监听 BoardPanel 的点击 → 合成走子请求）
第二版：CameraInputSource（OpenCV 抓帧识别 → 合成走子请求）

GameController 仅依赖 InputSource 接口，不关心走子从哪来。
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from core.board import Board


class InputSource(QObject):
    """走子来源抽象。

    信号：
        moveRequested(from_row, from_col, to_row, to_col) — 玩家决定走 from→to

    生命周期方法：
        start(board): 绑定当前对局的棋盘（鼠标版本里 board 用于校验点击的格是否己方子）
        stop(): 断开资源（摄像头版本里会释放 VideoCapture）
        set_enabled(enabled): AI 回合时由 controller 禁用输入，玩家回合再启用
    """

    moveRequested = Signal(int, int, int, int)

    def start(self, board: Board) -> None:
        raise NotImplementedError

    def stop(self) -> None:
        raise NotImplementedError

    def set_enabled(self, enabled: bool) -> None:
        raise NotImplementedError
