"""摄像头识别走子来源 —— 第二版实现。

当前仅保留骨架与接口签名，避免第二版上线时大改 controller。

预期实现：
- 构造参数：capture_device_index(摄像头编号), recognizer(BoardRecognizer)
- start() 打开摄像头并启动周期抓帧 QTimer
- stop() 释放 VideoCapture
- 每次抓帧 → 识别出 Board → 与上一次 diff
    - 恰好 2 处变化（一空一动）→ 合成 moveRequested
    - 恰好 1 处变化（吃子时己方棋子原地不动、敌子被替换）→ 扫描己方所有棋子找消失的格
    - 0 处或其他情况 → 忽略本帧，等待稳定
- 识别稳定性：连续 N 帧识别结果一致才触发 moveRequested，避免抖动
"""

from __future__ import annotations

from core.board import Board

from .base_input import InputSource


class CameraInputSource(InputSource):
    """占位：第二版接入 OpenCV 时填充实现。"""

    def __init__(self, capture_device_index: int = 0) -> None:
        super().__init__()
        self._device_index = capture_device_index
        # TODO(第二版): self._capture = cv2.VideoCapture(...)
        # TODO(第二版): self._recognizer = BoardRecognizer(...)
        # TODO(第二版): self._timer = QTimer(); self._timer.timeout.connect(self._on_tick)
        # TODO(第二版): self._last_board: Board | None = None

    def start(self, board: Board) -> None:  # pragma: no cover - 占位
        raise NotImplementedError("CameraInputSource 将在第二版实现")

    def stop(self) -> None:  # pragma: no cover - 占位
        raise NotImplementedError("CameraInputSource 将在第二版实现")

    def set_enabled(self, enabled: bool) -> None:  # pragma: no cover - 占位
        raise NotImplementedError("CameraInputSource 将在第二版实现")
