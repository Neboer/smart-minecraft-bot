# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

All Python commands must use the venv interpreter — `moderngl` and other dependencies are only installed there:

```powershell
# Run smoke tests (33 checks covering the full game flow)
.venv\Scripts\python.exe example.py

# Run the REPL player with visualizer (main entry point)
.venv\Scripts\python.exe -m interactive.human.replplayer

# Run the REPL player from a script file (useful for testing)
.venv\Scripts\python.exe -c "
from interactive.human.replplayer.REPLPlayer import main
main('interactive/human/replplayer/test_logic.txt', sleep_between=0.0)
"
```

There is no test framework — `example.py` is the authoritative test suite. Run it after every non-trivial change.

## Architecture

### Core game loop (`game/`)

The game is a discrete Minecraft-like sandbox with a probabilistic mutation system designed for MCTS/AI use. The world is 5×5×5. One tick = one player action + world simulation.

**Tick flow** (`game/game.py`):
1. `game_base_tick()` — collects pending player intents + world simulation, returns a combined `MutationGroupSequence`
2. `sample_sequence(rng)` — samples one `MutationSequence` from the probability space
3. `apply_mutation_sequence()` — executes mutations in order, each guarded by `check_conditions`
4. `do_physics()` — gravity → collision → bounds clamp, repeated until stable

**Multi-intent per tick**: `submit_player_intent` appends to a list. `game_base_tick` drains intents in order until their combined `tick_cost` reaches 1.0. `NoIntent.tick_cost == 0.0`; all others `== 1.0`.

### Probability model (`game/mutation/base.py`)

```
MutationGroupSequence  — Cartesian product of independent groups
  └── MutationGroup    — one independent event; mutually exclusive choices
        mutations: list[BaseMutation]
        weights:   list[float]         # parallel; uniform if empty
  └── MutationSequence — one drawn outcome (one mutation per group)
        probability: float             # joint probability of the draw
```

Probabilities live in `MutationGroup.weights`, **not** on individual mutations. `BaseMutation` has no `probability` field. `sample_sequence` picks one mutation from each group weighted by `weights`.

### Intent → Mutation pipeline

- **Intent** (`game/intent/`): player-bound, reads world state, returns `MutationGroupSequence`. Never mutates the world. `BaseIntent.build_mutation_group_sequence(world, player_id)`.
- **Mutation** (`game/mutation/`): world-changing unit with `check_conditions(world) → bool` and `execute(world) → None`. `SinglePlayerBaseMutation` carries a `player_id`.
- **Key invariant**: `assert player is not None` is the *only* permitted assert — it expresses the single-player guarantee. All other error conditions (missing block, full inventory, etc.) must be handled by returning False from `check_conditions` or early-returning from `execute`.

### New-dig timing

`DigIntent` for a **new** dig emits two groups in the same tick:
- Group 1: `BeginDigMutation` (sets `breaking_block`, `progress=0`, `target_time=N`)
- Group 2: `FinishDigMutation` if `N ≤ 1.0`, else `ContinueDigMutation`

This makes the begin tick count as 1 unit of work: sapling (1.0) breaks in 1 dig, plank (4.0) in 4 digs, plank+axe (2.0) in 2 digs.

### Block placement positions

Three reachable positions are distinct for place vs. dig:

| Player method | Position | Used by |
|---|---|---|
| `get_facing_block_position()` | (x+dx, y+dy, z) | both |
| `get_facing_block_position_high()` | (x+dx, y+dy, z+1) | both |
| `get_place_down_position()` | (x, y, z) — feet level | `place down` only |
| `get_position_below()` | (x, y, z−1) — under feet | `dig down` only |

`player.can_place_at()` uses `get_place_down_position()`; `player.can_reach_position()` uses `get_position_below()`. `PlaceBlockIntent` calls `can_place_at`; `DigIntent` calls `can_reach_position`.

### Data (`game/data.py`)

Single source of truth for all game constants: `BLOCK_BREAK_TIME`, `AXE_BREAK_MULTIPLIER`, `BLOCK_DROP_OPTIONS` (tuples of `(count, probability, item_type)`), `ITEM_MAX_STACK`, sapling growth constants. Import from here, never hard-code game values elsewhere.

### World validation (`game/world.py`)

Key methods:
- `is_valid_place_position(player, position, block_type)` — validates a player-specified placement target (no auto-selection; the player must specify the position)
- `can_player_move_to / can_player_step_up_to` — movement checks including 1-block step-up
- `build_mutation_group_sequence()` — sapling growth groups for all eligible saplings

### Interactive layer (`interactive/`)

- `interactive/Framework.py` — `Bot` base class with `propose_intent() → BaseIntent`; `run_bot_with_visualizer(bot_class)` launches bot thread + visualizer on main thread
- `interactive/human/replplayer/` — human REPL player:
  - `commands.py` — pure command parsing (`parse_line → BaseIntent | str`); `_place_target` and `_dig_target` are separate helpers (different "down" positions)
  - `REPLPlayer.py` — `run()` (no visualizer, REPL controls ticking) and `run_with_visualizer()` (REPL on thread, `game=None` to visualizer so renderer doesn't auto-tick)

### Coordinate system

`(x, y, z)`: x+ = East, y+ = South, z+ = Up. World is 5×5×5 (indices 0–4). `z == 0` is always adjacent to the implicit ground (blocks at z=0 can always be placed/reached without an explicit adjacent block).

### Visualizer (`visualize/viewer.py`)

`run_visualizer(world, player, game, world_lock)` blocks the main thread. When `game` is passed, it auto-ticks at 1 Hz. When `game=None`, it sets `_auto_refresh=True` and just re-renders from the live world state every frame — use this when the caller thread controls ticking.
