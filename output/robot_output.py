"""机械臂落子执行器 —— 第三版实现。

当前仅保留骨架与接口签名，避免第三版上线时大改 controller。

预期实现：
- 构造参数：robot_driver(机械臂 SDK 封装), confirmer(摄像头确认器)
- execute(move, board_after):
    1. 把内部 (row, col) 转为机械臂世界坐标 (x, y, z)
    2. 下发机械臂走子指令（吸起起点棋子 → 移动 → 放下）
    3. 如果是吃子，先把被吃棋子移到"废棋区"
    4. 机械臂回报完成 → 驱动摄像头抓一帧 → 识别 board_actual
    5. board_actual == board_after? 是则 emit moveExecuted；否则 emit moveFailed
- 失败恢复：moveFailed 后 controller 应暂停对局等待人工介入
"""

from __future__ import annotations

from core.board import Board, Move

from .base_output import MoveExecutor


class RobotExecutor(MoveExecutor):
    """占位：第三版接入机械臂时填充实现。"""

    def __init__(self) -> None:
        super().__init__()
        # TODO(第三版): self._robot = RobotDriver(...)
        # TODO(第三版): self._confirmer = VisionConfirmer(...)
        # TODO(第三版): self._coord_calibrator = CoordinateCalibrator(...)

    def execute(self, move: Move, board_after: Board) -> None:  # pragma: no cover - 占位
        raise NotImplementedError("RobotExecutor 将在第三版实现")
