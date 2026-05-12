"""全局配置。棋盘 / 引擎 / UI 可调参数集中在这里。"""

from __future__ import annotations

from pathlib import Path

# ---------- 路径 ----------
PROJECT_ROOT = Path(__file__).resolve().parent

# ---------- Pikafish 引擎 ----------
PIKAFISH_DIR = PROJECT_ROOT / "pikafish"
PIKAFISH_EXE = "pikafish-avx2.exe"                  # 需要换变体时直接改这里
PIKAFISH_NNUE = "pikafish.nnue"
ENGINE_THREADS = 1                                   # 单线程，避免与 GUI 抢 CPU
ENGINE_HASH_MB = 64
ENGINE_GO_TIMEOUT_EXTRA_MS = 2000                    # bestmove 等待超时 = movetime + 这个
ENGINE_STARTUP_TIMEOUT_SEC = 10                      # uciok / readyok 初始化超时

# ---------- IO 切换（第一版仅支持 mouse / screen） ----------
INPUT_SOURCE = "mouse"                               # "mouse" | "camera"(待实现)
OUTPUT_EXECUTOR = "screen"                           # "screen" | "robot"(待实现)

# ---------- 棋盘 ----------
BOARD_ROWS = 10                                      # 中国象棋 10 行
BOARD_COLS = 9                                       # 9 列
BOARD_MARGIN = 40                                    # 棋盘外边距
CELL_PIXEL = 56                                      # 单格像素（仅作初始默认，实际自适应）

# ---------- 窗口与面板 ----------
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 820
IMAGE_PANEL_MIN_WIDTH = 480                          # 左侧图像面板（第一版占位）
BOARD_PANEL_MIN_WIDTH = 600                          # 右侧虚拟棋盘最小宽

# ---------- 颜色（R, G, B） ----------
COLOR_BG = (236, 196, 121)                           # 木色棋盘
COLOR_LINE = (40, 30, 20)                            # 网格线
COLOR_RED_PIECE = (200, 30, 30)                      # 红方字/描边
COLOR_BLACK_PIECE = (30, 30, 30)                     # 黑方字/描边
COLOR_PIECE_FACE = (250, 230, 180)                   # 棋子底色（浅木色）
COLOR_LAST_MOVE_MARK = (220, 50, 50)                 # 最后一手高亮
COLOR_SELECTED_MARK = (50, 150, 220)                 # 当前选中高亮
COLOR_HOVER_MARK = (255, 255, 255, 70)               # 悬停淡白
