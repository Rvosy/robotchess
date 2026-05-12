# 中国象棋（Pikafish AI 版）

基于 PySide6 + Pikafish 开源引擎的中国象棋桌面对战程序。架构上预留了 OpenCV 摄像头识别与机械臂落子的扩展接口，第一版先把"虚拟棋盘 + AI 对战"链路跑通。

## 项目结构

```
象棋/
├── pikafish/                  # Pikafish 引擎二进制 + NNUE 权重（已就位）
│   ├── pikafish-avx2.exe      # 默认使用的 CPU 变体
│   ├── pikafish.nnue
│   └── ...                    # 其他 CPU 变体可手动切换
├── engine/                    # UCI 子进程封装层（IO 中性，不依赖 UI）
│   └── pikafish.py
├── core/                      # 棋盘数据 + 规则（待实现）
├── ai/                        # AI 适配层（待实现）
├── ui/                        # PySide6 界面（待实现）
├── input/                     # 走子来源抽象（鼠标 / 摄像头）
├── output/                    # 走子执行抽象（屏幕 / 机械臂）
├── config.py                  # 集中配置
├── requirements.txt
└── README.md
```

详细架构与设计权衡见 plan 文件 `pikafish-groovy-spindle.md`（在 `~/.claude/plans/`）。

## 环境准备

使用独立 conda 环境，避免污染主人现有的 `OpenCV` / `PyQt6` 等环境。

```powershell
# 1. 创建环境（Python 3.11）
conda create -n xiangqi python=3.11 -y

# 2. 激活
conda activate xiangqi

# 3. 安装依赖
pip install -r requirements.txt
```

环境一旦建好，之后每次开发只需 `conda activate xiangqi`。

## 引擎自测

写完 `engine/pikafish.py` 后，可以独立验证引擎能否启动、坐标方向是否正确：

```powershell
conda activate xiangqi
cd D:/Project/Python/图像处理课程设计/象棋
python -m engine.pikafish
```

正常输出（最关键的几行）：

```
[smoke] options (20): ['Clear Hash', ..., 'Skill Level', 'Threads', 'UCI_Elo', 'UCI_LimitStrength', ...]
[smoke] bestmove: b2e2
[smoke] 通信与走法格式校验通过
```

- `b2e2` = 红方开局炮二平五，是 Pikafish 在 500ms 思考下的标准开局之一
- 看到 `bestmove` 列字母在 `a..i`、行数字在 `0..9` 即视为通信链路打通
- 输出里中文如果乱码是 Windows 终端 GBK 解 UTF-8 的问题，不影响程序逻辑；要看清楚的话用 `chcp 65001` 切到 UTF-8 终端

## 难度档位（设计中）

| 档位 | movetime | Skill Level | 说明                |
| ---- | -------- | ----------- | ------------------- |
| 简单 | 200 ms   | 0           | 给新手练手          |
| 普通 | 500 ms   | 5           | 日常对弈            |
| 困难 | 1500 ms  | 15          | 中级棋手挑战        |
| 噩梦 | 3000 ms  | 20          | 接近引擎全力        |

Pikafish 启动时实测支持 `Skill Level` / `UCI_LimitStrength` / `UCI_Elo` 等弱化选项，方案可行。

## 当前进度

- [x] 项目骨架（config.py / requirements.txt / 目录结构）
- [x] `engine/pikafish.py` UCI 通信封装 + 烟雾测试通过
- [ ] `core/` 棋盘数据 + FEN
- [ ] `core/rule.py` 走法规则
- [ ] `ai/` 三件套
- [ ] `input/` `output/` 抽象层
- [ ] `ui/` 四件套（main_window / image_panel / board_panel / settings_dialog）
- [ ] `main.py` 控制器联调
- [ ] 手测与回归

## 未来扩展（第二/三版）

- **OpenCV 识别**：实现 `input/camera_input.py`，左侧 `ImagePanel` 显示摄像头画面；`core/engine/ai/ui` 完全不动
- **机械臂落子**：实现 `output/robot_output.py`，发出物理走子指令并等摄像头确认到位；controller 已经按异步执行链设计，零改动
- **棋谱保存 / 复盘**：`Board` 已天然维护走子历史，按需追加序列化即可

## 切换 CPU 变体

`pikafish/` 目录下提供多个变体（`avx2` / `avx512` / `vnni512` / `bmi2` 等）。如果主人想换更强的变体，改 `config.py` 里的 `PIKAFISH_EXE` 即可：

```python
PIKAFISH_EXE = "pikafish-vnni512.exe"
```

性能优先级（来自 `pikafish/引擎介绍.txt`）：

```
vnni512 > bw512 > avx512 > avxvnni > bmi2 > avx2 > sse41-popcnt
```

默认 `avx2` 兼容性最好。
