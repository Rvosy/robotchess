[English](README.md) | [中文](README.zh.md)

# robotchess

> A Chinese chess (Xiangqi) desktop app that plays against the open-source **Pikafish** engine — designed from day one to be driven by a camera and a robotic arm, not just a mouse.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![PySide6](https://img.shields.io/badge/PySide6-6.6+-41CD52?logo=qt&logoColor=white)
![Pikafish](https://img.shields.io/badge/Engine-Pikafish-orange)
![License](https://img.shields.io/badge/license-MIT-blue)

---

## Why this exists

The end goal is a physical Xiangqi setup: a camera watches the board, a robotic arm moves the pieces, and the AI behind it has to be strong enough that beating it is actually rewarding. That last part rules out almost every hobbyist Xiangqi project — most ship with a hand-rolled minimax that an intermediate human beats in 5 minutes.

**Pikafish** is the open-source Stockfish-equivalent for Chinese chess: NNUE-based, top-tier strength, free. Wiring it to a real GUI (and eventually to OpenCV + a robot arm) is the actual problem.

This v1 ships the **virtual side** of that system. Real GUI, real Pikafish, real rules — but mouse input and screen output. The architecture leaves the camera and robot slots open: when v2 swaps the input source and v3 swaps the output executor, `core/`, `engine/`, and `ai/` will not change a single line.

## What it is

A PySide6 desktop application:

- 9×10 board with full Xiangqi rules (palace, river, advisor diagonals, elephant eye, horse leg, cannon screen, flying general, self-check filtering, checkmate, stalemate)
- Pikafish UCI subprocess managed transparently — startup, NNUE loading, `Skill Level` / `movetime` per difficulty, graceful shutdown
- 4 difficulty tiers from "first-time learner" to "engine at full strength"
- Two-click move interaction with last-move highlight, selection ring, hover preview, and check warnings
- Async move-execution pipeline ready for a future robot arm — controller waits on `moveExecuted` signal regardless of whether the executor is a screen refresh or a 5-second physical motion

## Key features

- **Pikafish under the hood, not a toy minimax.** The AI is the real Pikafish binary speaking UCI on stdin/stdout. Difficulty maps to `Skill Level` 0/5/15/20 plus `movetime` 200/500/1500/3000 ms — at "Nightmare" it plays at engine strength, no nerfs.

- **Rule layer that actually passes the standard tests.** Opening legal-move count for both sides = 44 (the canonical Xiangqi number). Flying general, self-check filtering, palace/river/eye constraints all unit-tested in `core/rule.py`.

- **IO is abstract from day one.** `InputSource` and `MoveExecutor` are PySide6 `QObject`s with signals; `MouseInputSource` and `ScreenExecutor` are concrete v1 implementations; `CameraInputSource` and `RobotExecutor` are scaffolded files with the exact same interface, ready to be filled in for v2/v3 without touching the controller.

- **Async move pipeline.** When the player or AI commits a move, the controller calls `executor.execute(move)` and waits for the `moveExecuted` signal before advancing turns. Screen v1 emits immediately; robot arm v3 emits only after the camera confirms the piece is physically in place. Same state machine, no rewrite.

- **FEN-native board with diff support.** `Board.to_fen()` round-trips perfectly with Pikafish; `Board.diff(other)` returns per-cell changes — primitive that v2 will use to compare "what the camera sees" against "what we believe the board is."

## With / Without

|                       | Hand-rolled hobby project       | robotchess                                                 |
| --------------------- | ------------------------------- | ---------------------------------------------------------- |
| Engine                | Local minimax / heuristic       | Pikafish NNUE via UCI                                      |
| Strength at top tier  | Beatable by intermediate human  | Engine-grade; same binary as serious analysis tools        |
| Rule completeness     | Often missing flying general / self-check | Full rules, opening legal moves = 44 (verified)    |
| Input model           | Hardcoded mouse                 | `InputSource` interface (mouse v1, camera v2 scaffolded)   |
| Output model          | Hardcoded screen redraw         | `MoveExecutor` interface (screen v1, robot v3 scaffolded)  |
| Move pipeline         | Synchronous                     | Async signal-driven, ready for physical actuation latency  |
| Board representation  | Ad-hoc 2D array                 | FEN-native, with `diff()` for vision reconciliation        |

## How it works

### Three-layer architecture

```
+------------------+   moveRequested(fr,fc,tr,tc)   +------------------+
|   InputSource    | ------------------------------>|                  |
|  mouse / camera  |                                |                  |
+------------------+                                | GameController   |
+------------------+   moveExecuted / moveFailed    |  (state machine) |
|  MoveExecutor    | <------------------------------|                  |
|  screen / robot  |                                +------------------+
+------------------+                                          |
                                                              v
                                              +-------------------------+
                                              | core + engine + ai      |
                                              | (no UI, no IO coupling) |
                                              +-------------------------+
```

The controller never touches `BoardPanel.set_cell` or `engine.go` directly. It only talks to abstract `InputSource` and `MoveExecutor`. Swapping mouse → camera or screen → robot is a constructor change in `main.py`, nothing else.

### Engine integration

`engine/pikafish.py` is a thin synchronous UCI client (~250 lines). It launches `pikafish-avx2.exe` with `cwd` set to the binary's directory so the NNUE loads without absolute-path encoding issues on Windows Chinese paths. It parses the engine's `option` lines on startup, exposing `supports_option()` so the difficulty factory knows whether `Skill Level` is actually available before sending it.

```python
# Each AI turn, in a QThread to keep the UI responsive:
fen = board.to_fen()
uci = engine.go(fen, movetime_ms=1500)   # blocks until "bestmove ..."
(fr, fc), (tr, tc) = parse_uci_move(uci) # "h2e2" -> ((7,7),(7,4))
```

The board's coordinate system was chosen to match UCI exactly — `row=0` is the black back rank (FEN's first row), `row=9` is the red back rank. Conversion is `uci_rank = 9 - row`. Picked this on purpose to avoid the most common Xiangqi-engine bug: silent vertical flips.

### Why async execution, even on screen

`ScreenExecutor.execute()` could just call `panel.update()` and return. Instead it queues the `moveExecuted` signal via `QTimer.singleShot(0, ...)`. The reason: `RobotExecutor` (v3) cannot be synchronous — the arm physically takes seconds to move. By forcing the v1 path to also be async, the controller's state machine is *already* what v3 needs. No "now make it async" refactor later.

### Design decisions

| Choice | Why |
| --- | --- |
| Bundled Pikafish binary, not python-chess | python-chess does not support Xiangqi. Subprocess UCI is the only path. |
| Send full FEN every turn (not `position startpos moves ...`) | One source of truth. Cannot get out of sync if the controller and engine disagree on history. |
| Integer-encoded board cells (`±1..±7`) | `sign` gives color, `abs` gives type. No dict lookups in the rule hot path. |
| `Board.diff()` shipped in v1 | v2 (camera) needs it to reconcile vision results against believed state. Cheaper to write now than retrofit. |
| Difficulty switch without engine restart | Each `PikafishAI` writes its own `Skill Level` via `setoption` before each `go`. Engine instance is a singleton. |

## Quick start

**Prerequisites**
- Windows 10/11 (other OS work but `pikafish-avx2.exe` is Windows; download the matching binary from [Pikafish releases](https://github.com/official-pikafish/Pikafish/releases))
- Python 3.11+ (Anaconda/Miniconda recommended)

```powershell
# 1. Clone
git clone https://github.com/<your-name>/robotchess.git
cd robotchess

# 2. Drop Pikafish binaries into pikafish/
#    The folder must contain pikafish-avx2.exe + pikafish.nnue (or another variant)
#    Get them from https://github.com/official-pikafish/Pikafish/releases

# 3. Create env and install deps
conda create -n xiangqi python=3.11 -y
conda activate xiangqi
pip install -r requirements.txt

# 4. Run
python main.py
```

A "Pikafish 引擎" titled window opens. You play Red by default; click any red piece to select, click destination to move. The status bar shows whose turn, current difficulty, and check warnings.

### Verify the engine without launching the GUI

```powershell
python -m engine.pikafish
```

Expected output ends with `[smoke] bestmove: b2e2` — that's Pikafish playing 炮二平五 (cannon to center) as opening, confirming UCI handshake + coordinate system both work.

### End-to-end smoke test

```powershell
python tests/test_end_to_end.py
```

Launches the full GUI, simulates a player move (马二进三), waits for AI reply, validates legality, exits. Total runtime ~1 second.

## Roadmap

- **v2 — Camera input.** Implement `input/camera_input.py`: OpenCV `VideoCapture` + a board recognizer. Frame stream → 9×10 piece matrix → `Board.diff()` against believed state → emit `moveRequested`. The left `ImagePanel` shows the live feed with recognition overlay.
- **v3 — Robot arm output.** Implement `output/robot_output.py`: `(row, col)` → physical coordinates → arm command → wait for completion → camera reconfirm → emit `moveExecuted` (or `moveFailed` if the piece didn't land).
- **Game record / replay.** `Board.move_history` already collects every move; just needs PGN-style serialization.

## Project layout

```
robotchess/
├── pikafish/             # ← drop binaries here (gitignored)
├── engine/pikafish.py    # UCI subprocess wrapper
├── core/
│   ├── board.py          # 10×9 board, FEN, move history, diff()
│   ├── constants.py      # piece encoding, palace/river bounds
│   ├── pieces.py         # FEN ↔ integer ↔ Chinese character maps
│   └── rule.py           # legal moves, check, mate, stalemate
├── ai/
│   ├── base_ai.py        # BaseAI interface
│   ├── pikafish_ai.py    # Pikafish adapter + UCI move parser
│   └── factory.py        # difficulty → (movetime, skill_level)
├── input/
│   ├── base_input.py     # InputSource ABC (Qt signals)
│   ├── mouse_input.py    # v1: BoardPanel clicks
│   └── camera_input.py   # v2 scaffold
├── output/
│   ├── base_output.py    # MoveExecutor ABC
│   ├── screen_output.py  # v1: panel refresh
│   └── robot_output.py   # v3 scaffold
├── ui/
│   ├── main_window.py    # QSplitter layout
│   ├── image_panel.py    # left: camera feed (placeholder in v1)
│   ├── board_panel.py    # right: 9×10 board + two-click interaction
│   ├── settings_dialog.py
│   ├── status_bar.py
│   └── ai_worker.py      # QThread for engine.go()
├── tests/test_end_to_end.py
├── main.py               # GameController state machine
├── config.py
└── requirements.txt
```

## License

MIT. Pikafish is GPLv3 — its binaries are not redistributed in this repo; download them yourself from the [official release page](https://github.com/official-pikafish/Pikafish/releases).

## Acknowledgments

- [Pikafish](https://github.com/official-pikafish/Pikafish) — the engine that makes this project worth building.
- [Stockfish](https://github.com/official-stockfish/Stockfish) — Pikafish's upstream lineage and the reason its UCI flow is so well-trodden.
