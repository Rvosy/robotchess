<!-- Synced with README.md as of 2026-05-13 -->

[English](README.md) | [中文](README.zh.md)

# robotchess

> 一个能跟开源象棋引擎 **Pikafish** 对弈的中国象棋桌面程序——从第一行代码开始，就是为接摄像头和机械臂准备的，不只是给鼠标用的。

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![PySide6](https://img.shields.io/badge/PySide6-6.6+-41CD52?logo=qt&logoColor=white)
![Pikafish](https://img.shields.io/badge/Engine-Pikafish-orange)
![License](https://img.shields.io/badge/license-MIT-blue)

---

## 为什么有这个项目

终极目标是一套真实的象棋系统：摄像头看棋盘，机械臂动棋子，背后的 AI 要强到能让人下得有成就感。最后这一条，就把绝大多数业余象棋项目排除掉了——大部分项目自带的是手搓 minimax，业余棋手 5 分钟就能赢。

**Pikafish** 是中国象棋圈的开源 Stockfish：NNUE 神经网络、顶级棋力、免费。把它接到一个真正的 GUI 上（再往下接 OpenCV 和机械臂），才是真正的工程问题。

v1 把这个系统的「虚拟那一半」做完。真实 GUI、真实 Pikafish、完整规则——但还是鼠标输入、屏幕输出。架构上把摄像头和机械臂的位置预留好了：v2 换 input、v3 换 output 的时候，`core/`、`engine/`、`ai/` 一行不用改。

## 它是什么

一个 PySide6 桌面应用：

- 9×10 棋盘 + 完整中国象棋规则（九宫、过河、士斜线、象眼、马腿、炮架、飞将、自将过滤、将死、困毙）
- Pikafish 子进程托管：启动、加载 NNUE、按难度配 `Skill Level` / `movetime`、退出时优雅关闭
- 4 档难度，从「第一次摸象棋」到「引擎全力」
- 两步点击走子，含最后一手高亮、选中圈、悬停提示、被将军弹窗
- 异步走子执行管线——controller 等 `moveExecuted` 信号才推进回合，不管对面是 0 毫秒的屏幕刷新，还是 5 秒的机械臂物理动作

## 真正差异化的点

- **底层是 Pikafish，不是玩具 minimax。** AI 真就是 Pikafish 二进制本体，通过 UCI 协议在 stdin/stdout 上对话。难度直接映射到 `Skill Level` 0/5/15/20 加上 `movetime` 200/500/1500/3000ms——「噩梦」档就是引擎全力，没有任何阉割。

- **规则层经得起标准测试。** 双方开局合法走法数 = 44（中国象棋的标准答案）。飞将、自将过滤、九宫/过河/塞象眼/蹩马腿全在 `core/rule.py` 单元测试覆盖范围内。

- **IO 第一天就是抽象的。** `InputSource` 和 `MoveExecutor` 都是带信号的 PySide6 `QObject`；`MouseInputSource` / `ScreenExecutor` 是 v1 的具体实现；`CameraInputSource` / `RobotExecutor` 是已经搭好骨架的占位文件，接口一模一样，v2/v3 只需填实现，不动 controller。

- **异步走子管线。** 玩家或 AI 提交走子后，controller 调 `executor.execute(move)` 然后**等** `moveExecuted` 信号，才切下一回合。屏幕版立刻发信号；机械臂版要等摄像头确认棋子物理到位才发。同一个状态机，不需要重写。

- **棋盘原生支持 FEN 与 diff。** `Board.to_fen()` 跟 Pikafish 完美往返；`Board.diff(other)` 返回逐格差异——这个原语是 v2 留给视觉对比用的：「摄像头看到的」 vs.「我们以为的」。

## 跟一般业余项目对比

|                | 手搓业余项目                       | robotchess                                       |
| -------------- | -------------------------------- | ------------------------------------------------ |
| AI 引擎         | 本地 minimax / 启发式             | 通过 UCI 接 Pikafish NNUE                          |
| 高难度强度      | 业余棋手能赢                      | 引擎级，跟严肃分析工具用同一个二进制                |
| 规则完整度      | 经常缺飞将 / 自将过滤             | 完整规则，开局合法走法 = 44（已验证）              |
| 输入模型        | 鼠标写死                          | `InputSource` 接口，鼠标 v1 + 摄像头 v2 已搭骨架  |
| 输出模型        | 屏幕重绘写死                      | `MoveExecutor` 接口，屏幕 v1 + 机械臂 v3 已搭骨架 |
| 走子管线        | 同步                              | 信号驱动的异步，能容忍物理动作的延迟               |
| 棋盘表示        | 临时 2D 数组                      | 原生 FEN，附 `diff()` 用于视觉对账                 |

## 架构

### 三层正交

```
+------------------+   moveRequested(fr,fc,tr,tc)   +------------------+
|   InputSource    | ------------------------------>|                  |
|  鼠标 / 摄像头   |                                |                  |
+------------------+                                | GameController   |
+------------------+   moveExecuted / moveFailed    |   (状态机)        |
|  MoveExecutor    | <------------------------------|                  |
|  屏幕 / 机械臂   |                                +------------------+
+------------------+                                          |
                                                              v
                                              +-------------------------+
                                              |  core + engine + ai     |
                                              |  (无 UI / 无 IO 耦合)    |
                                              +-------------------------+
```

Controller 永远不直接动 `BoardPanel.set_cell` 或者 `engine.go`，只跟抽象的 `InputSource` 和 `MoveExecutor` 通信。鼠标换摄像头、屏幕换机械臂，本质上就是改 `main.py` 里的构造函数那一两行。

### 引擎接入

`engine/pikafish.py` 是个轻量的同步 UCI 客户端（约 250 行）。启动时把 `cwd` 设到 `pikafish/` 目录下，让引擎自己加载同目录的 NNUE——绕开了「Windows 中文路径 → UTF-8 管道 → 引擎 ANSI 解码 → fopen 失败」这个坑。启动阶段解析引擎自报的 `option` 行，对外暴露 `supports_option()`，让难度工厂知道当前版本到底支不支持 `Skill Level`，再决定要不要发。

```python
# 每个 AI 回合，在 QThread 里跑，避免阻塞 UI：
fen = board.to_fen()
uci = engine.go(fen, movetime_ms=1500)   # 阻塞等 "bestmove ..."
(fr, fc), (tr, tc) = parse_uci_move(uci) # "h2e2" -> ((7,7),(7,4))
```

棋盘坐标系故意跟 UCI 完全对齐：`row=0` 是黑方底线（FEN 第一行），`row=9` 是红方底线。换算就一条 `uci_rank = 9 - row`。这么选是为了避开象棋引擎接入最容易踩的坑——上下翻转无声故障。

### 屏幕版为什么也要异步

`ScreenExecutor.execute()` 大可以直接 `panel.update()` 然后返回。但实现里特意用 `QTimer.singleShot(0, ...)` 把 `moveExecuted` 信号排到下一帧。原因：v3 的 `RobotExecutor` 不可能同步——机械臂物理动作要好几秒。把 v1 的路径也写成异步的，controller 状态机现在长的就是 v3 需要的样子，以后不需要「现在改成异步」这种返工。

### 关键决策

| 选择 | 原因 |
| --- | --- |
| 自带 Pikafish 二进制，不用 python-chess | python-chess 不支持中国象棋，子进程 UCI 是唯一路径 |
| 每回合发完整 FEN，不用 `position startpos moves ...` | 单一事实来源，引擎和 controller 不会因为历史漂移而失同步 |
| 棋子用整数编码（`±1..±7`） | `sign` 给颜色、`abs` 给类型，规则热路径不用查 dict |
| `Board.diff()` v1 就写好 | v2 摄像头要靠它对账识别结果。现在写比以后回填便宜 |
| 难度切换不重启引擎 | 每个 `PikafishAI` 在 `go` 之前自己 `setoption` 写一次 `Skill Level`，引擎实例是单例 |

## 快速开始

**前置条件**
- Windows 10/11（其他系统也行，但仓库里默认用 `pikafish-avx2.exe`，从 [Pikafish releases](https://github.com/official-pikafish/Pikafish/releases) 下对应平台的）
- Python 3.11+（推荐用 Anaconda/Miniconda）

```powershell
# 1. 克隆
git clone https://github.com/<your-name>/robotchess.git
cd robotchess

# 2. 把 Pikafish 二进制放进 pikafish/ 目录
#    至少需要 pikafish-avx2.exe + pikafish.nnue（或者其他变体）
#    下载页：https://github.com/official-pikafish/Pikafish/releases

# 3. 建环境装依赖
conda create -n xiangqi python=3.11 -y
conda activate xiangqi
pip install -r requirements.txt

# 4. 跑
python main.py
```

会打开一个标题「中国象棋（Pikafish 引擎）」的窗口。默认玩家执红，点己方棋子选中、点目标点走子，状态栏显示当前回合、难度、将军提示。

### 不开 GUI 单独验证引擎

```powershell
python -m engine.pikafish
```

正常情况最后会打 `[smoke] bestmove: b2e2`——这是 Pikafish 走的「炮二平五」开局，确认 UCI 握手和坐标系都正常。

### 端到端烟雾测试

```powershell
python tests/test_end_to_end.py
```

完整启动 GUI，模拟玩家走「马二进三」，等 AI 应一手，校验合法性，退出。整个流程 ~1 秒。

## 路线图

- **v2 — 摄像头输入。** 实现 `input/camera_input.py`：OpenCV `VideoCapture` + 棋盘识别器。每帧 → 9×10 棋子矩阵 → `Board.diff()` 跟内部状态对比 → emit `moveRequested`。左侧 `ImagePanel` 同时显示实时画面和识别叠加。
- **v3 — 机械臂输出。** 实现 `output/robot_output.py`：`(row, col)` → 物理坐标 → 机械臂指令 → 等动作完成 → 摄像头复检 → emit `moveExecuted`（或 `moveFailed` 如果棋子没到位）。
- **棋谱 / 复盘。** `Board.move_history` 已经天然记录了每一步，缺的只是 PGN 风格的序列化。

## 项目结构

```
robotchess/
├── pikafish/             # ← 二进制放这里（已 gitignore）
├── engine/pikafish.py    # UCI 子进程封装
├── core/
│   ├── board.py          # 10×9 棋盘、FEN、走子历史、diff()
│   ├── constants.py      # 棋子编码、九宫/河界
│   ├── pieces.py         # FEN ↔ 整数 ↔ 中文字 三向映射
│   └── rule.py           # 合法走法、将军、将死、困毙
├── ai/
│   ├── base_ai.py        # BaseAI 接口
│   ├── pikafish_ai.py    # Pikafish 适配 + UCI 走法解析
│   └── factory.py        # 难度 → (movetime, skill_level)
├── input/
│   ├── base_input.py     # InputSource 抽象（Qt 信号）
│   ├── mouse_input.py    # v1：BoardPanel 点击
│   └── camera_input.py   # v2 占位
├── output/
│   ├── base_output.py    # MoveExecutor 抽象
│   ├── screen_output.py  # v1：面板刷新
│   └── robot_output.py   # v3 占位
├── ui/
│   ├── main_window.py    # QSplitter 双面板
│   ├── image_panel.py    # 左：摄像头画面（v1 占位）
│   ├── board_panel.py    # 右：9×10 棋盘 + 两步点击
│   ├── settings_dialog.py
│   ├── status_bar.py
│   └── ai_worker.py      # QThread 跑 engine.go()
├── tests/test_end_to_end.py
├── main.py               # GameController 状态机
├── config.py
└── requirements.txt
```

## 协议

MIT。Pikafish 本身是 GPLv3，其二进制不随仓库分发，请自行从 [官方 release 页](https://github.com/official-pikafish/Pikafish/releases) 下载。

## 致谢

- [Pikafish](https://github.com/official-pikafish/Pikafish) —— 让这个项目值得做的引擎。
- [Stockfish](https://github.com/official-stockfish/Stockfish) —— Pikafish 的上游血统，也是它 UCI 流程如此成熟的原因。
