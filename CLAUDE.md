# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

This repository implements a Minecraft-inspired block-based sandbox game with a 5×5×5 world, basic block types (sapling, plank, leaf), player inventory and crafting, and a simple growth mechanic for saplings. The game is designed to use as a testbed for AI agents that can interact with the world through a defined set of intents. All visualization is used for developer to diagnostic purposes and is not intended to be a polished game client.

## Commands

All Python commands must use the venv interpreter.

```powershell
# Run smoke tests (authoritative test suite)
.venv\Scripts\python.exe example.py
```

There is no test framework — `example.py` is the authoritative test suite. Run it after every non-trivial change.

## Game Mechanics

### World

5×5×5 grid. Coordinate system: `(x, y, z)` where x+ = East, y+ = Up (altitude), z+ = South (indices 0–4). `y == 0` is always adjacent to the implicit ground — blocks at y=0 can be placed/reached without an explicit adjacent block.

### Block types and properties

| Block | Break time | Drop | Notes |
|-------|-----------|------|-------|
| SAPLING | 1.0 tick | 1× SAPLING | Can grow into a tree |
| PLANK | 4.0 ticks | 1× PLANK | 2.0 ticks with WOODEN_AXE |
| LEAF | 1.0 tick | 1–3× SAPLING (random) | Tree canopy |

### Items and stacking

| Item | Max stack |
|------|-----------|
| SAPLING | 8 |
| PLANK | 8 |
| WOODEN_AXE | 1 |

### Crafting

- **Wooden axe**: 3× PLANK → 1× WOODEN_AXE (via `CraftAxeIntent`)
- Crafting fails if the inventory has no room for the result.

### Tree growth

Saplings at `z == 0` with no other blocks in the same xy column or adjacent xy columns may grow each tick with probability 0.1. Trunk heights: 2, 3, or 4 (equal probability). Growth places PLANK trunk blocks and LEAF canopy. Probability 0.9 the sapling stays idle.

### Inventory (hotbar)

The player has a **9-slot hotbar** (`player.inventory`, indices 0–8). One slot is the **active slot** (`player._active_slot`, default 0); `player.main_hand_slot` returns it, `player.main_hand_item` returns its item.

When items drop into inventory (e.g. from digging):
- Items stack onto existing slots of the same type first, then fill empty slots.
- Overflow is **silently discarded** — the dig/action still completes even when the inventory is full.

### Player reach (dig vs. place)

The player is 2 blocks tall. Reachable positions:

**Dig** (`can_reach_position`): facing (foot level), facing-high (head level), below feet, above head, down-front (one ahead + one below feet).

**Place** (`can_place_at`): facing (foot level), facing-high (head level), own body position (pillar-up), down-front (bridging), above head.

Placing at the player's own body position (pillar-up): non-sapling blocks require the block above the player's head to be clear; saplings may only be placed at `z == 0`.

---

## Architecture

### Core game loop (`game/`)

One tick = one player action + world simulation.

**Tick flow** (`game/game.py`):
1. `game_base_tick()` — collects pending player intents + world simulation, returns a combined `MutationGroupSequence`
2. `sample_sequence(rng)` — samples one `MutationSequence` from the probability space
3. `apply_mutation_sequence()` — executes mutations in order, each guarded by `check_conditions`
4. `do_physics()` — gravity → collision → bounds clamp, repeated until stable

### Multi-intent per tick

`submit_player_intent` appends to a list; `game_base_tick` drains intents in order, stopping when their combined `tick_cost` would exceed 1.0.

**0-tick intents** (free, combinable before a 1-tick action in the same submission):
- `NoIntent` — do nothing; abandons an active dig
- `TurnIntent` — change facing direction; abandons an active dig
- `ChangeActiveSlotIntent` — switch active hotbar slot; does **not** abandon a dig

**1-tick intents**:
- `WalkIntent`, `DigIntent`, `PlaceBlockIntent`, `CraftAxeIntent`
- `DropOneIntent` — drop 1 item from active slot (or specified slot); abandons dig
- `DropStackIntent` — drop entire stack from active slot (or specified slot); abandons dig

Dropped items are deleted (no world entity). Both drop intents accept an optional `slot` parameter; default is `player.main_hand_slot`.

### Probability model (`game/mutation/base.py`)

```
MutationGroupSequence  — Cartesian product of independent groups
  └── MutationGroup    — one independent event; mutually exclusive choices
        mutations: list[BaseMutation]
        weights:   list[float]         # parallel; uniform if empty
  └── MutationSequence — one drawn outcome (one mutation per group)
        probability: float             # joint probability of the draw
```

Probabilities live in `MutationGroup.weights`, **not** on individual mutations. `BaseMutation` has no `probability` field.

### Intent → Mutation pipeline

- **Intent** (`game/intent/`): player-bound, reads world state, returns `MutationGroupSequence`. Never mutates the world. `BaseIntent.build_mutation_group_sequence(world, player_id)`.
- **Mutation** (`game/mutation/`): world-changing unit with `check_conditions(world) → bool` and `execute(world) → None`. `SinglePlayerBaseMutation` carries a `player_id`.
- **Key invariant**: `assert player is not None` is the *only* permitted assert. All other error conditions must be handled by returning `False` from `check_conditions` or early-returning from `execute`.

### New-dig timing

`DigIntent` for a **new** dig emits two groups in the same tick:
- Group 1: `BeginDigMutation` (sets `breaking_block`, `progress=0`, `target_time=N`)
- Group 2: `FinishDigMutation` if `N ≤ 1.0`, else `ContinueDigMutation`

This makes the begin tick count as 1 unit of work: sapling (1.0) breaks in 1 dig, plank (4.0) in 4 digs, plank+axe (2.0) in 2 digs.

### Data (`game/data.py`)

Single source of truth for all game constants: `BLOCK_BREAK_TIME`, `AXE_BREAK_MULTIPLIER`, `BLOCK_DROP_OPTIONS` (tuples of `(count, probability, item_type)`), `ITEM_MAX_STACK`, sapling growth constants. Import from here, never hard-code game values elsewhere.

### World validation (`game/world.py`)

Key methods:
- `is_valid_place_position(player, position, block_type)` — validates a player-specified placement target
- `can_player_move_to / can_player_step_up_to` — movement checks including 1-block step-up
- `build_mutation_group_sequence()` — sapling growth groups for all eligible saplings

### Deprecated code

`interactive/reinforcementai` is a failure and must not be used as a reference for new code.
