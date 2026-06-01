"""Gymnasium environment wrapping the smart-bot game world.

The goal is to collect as many Planks as possible in minimum time.
Reward = number of planks added to the player's inventory each tick.
Episodes are truncated after max_steps ticks; there is no terminal state.

Action space  (Discrete, 22 actions):
    See ACTION_* constants and ACTION_NAMES below.

Observation space (Dict):
    world               int8  (5,5,5)  — block type at each voxel
                                         0=empty 1=sapling 2=plank 3=leaf
    player_pos          int8  (3,)     — [x, y, z]  each in 0..4
    player_dir          int8  (1,)     — 0=East 1=South 2=West 3=North
    inventory           int8  (10,2)   — [[item_type, count], …] per slot
                                         item_type: 0=empty 1=sapling
                                                     2=plank 3=wooden_axe
    is_breaking         int8  (1,)     — 1 if actively digging, else 0
    break_progress_ratio float32 (1,)  — progress/target_time, 0 if idle
"""
from __future__ import annotations

from typing import Any, Optional

import numpy as np
import gymnasium as gym
from gymnasium.spaces import Box, Dict as DictSpace, Discrete

from game.core import BlockType, Direction, ItemType, Vec3I
from game.game import Game
from game.player import Player
from game.intent import (
    CraftAxeIntent,
    DigIntent,
    NoIntent,
    PlaceBlockIntent,
    SwapInventoryIntent,
    TurnIntent,
    WalkIntent,
)
from game.intent.base import BaseIntent
from interactive.reinforcementai.reward import (
    RewardConfig,
    DEFAULT_CONFIG,
    StateSnapshot,
    take_snapshot,
    compute_reward,
)

# ── Encoding tables ──────────────────────────────────────────────────────────

_BLOCK_ENCODE: dict[BlockType, int] = {
    BlockType.SAPLING: 1,
    BlockType.PLANK:   2,
    BlockType.LEAF:    3,
}
_ITEM_ENCODE: dict[ItemType, int] = {
    ItemType.SAPLING:    1,
    ItemType.PLANK:      2,
    ItemType.WOODEN_AXE: 3,
}
# Absolute direction list — index matches player_dir encoding
_DIRECTIONS = [Direction.EAST, Direction.SOUTH, Direction.WEST, Direction.NORTH]
_DIR_ENCODE: dict[Direction, int] = {d: i for i, d in enumerate(_DIRECTIONS)}

# ItemType → BlockType (for place actions)
_ITEM_TO_BLOCK: dict[ItemType, BlockType] = {}
for _bt in BlockType:
    _ITEM_TO_BLOCK.setdefault(_bt.to_item_type(), _bt)

# ── Action indices ────────────────────────────────────────────────────────────

ACTION_NOOP        = 0
ACTION_MOVE        = 1
ACTION_TURN_EAST   = 2
ACTION_TURN_SOUTH  = 3
ACTION_TURN_WEST   = 4
ACTION_TURN_NORTH  = 5
ACTION_PLACE_LOW   = 6
ACTION_PLACE_HIGH  = 7
ACTION_PLACE_DOWN  = 8
ACTION_DIG_LOW     = 9
ACTION_DIG_HIGH    = 10
ACTION_DIG_DOWN    = 11
# swap main-hand (slot 0) with slots 1..9
ACTION_SWAP_BASE   = 12   # ACTION_SWAP_BASE + (slot - 1) for slot in 1..9
ACTION_CRAFT_AXE   = 21
N_ACTIONS          = 22

ACTION_NAMES: list[str] = [
    "noop",
    "move",
    "turn_east", "turn_south", "turn_west", "turn_north",
    "place_low", "place_high", "place_down",
    "dig_low",   "dig_high",   "dig_down",
    "swap_1", "swap_2", "swap_3", "swap_4",
    "swap_5", "swap_6", "swap_7", "swap_8", "swap_9",
    "craft_axe",
]

_WS = 5  # world size


class WorldGYM(gym.Env):
    """Gymnasium environment for the smart-bot Minecraft-like world.

    Parameters
    ----------
    seed:      RNG seed for deterministic episodes (None = non-deterministic).
    max_steps: Episode truncation horizon.
    """

    metadata = {"render_modes": []}

    def __init__(
        self,
        seed: Optional[int] = None,
        max_steps: int = 500,
        reward_config: RewardConfig = DEFAULT_CONFIG,
    ) -> None:
        super().__init__()
        self._max_steps = max_steps
        self._reward_cfg = reward_config
        self._game = Game(seed=seed)
        self._player_id: str = ""
        self._player: Optional[Player] = None  # set in reset()
        self._prev_action: int = ACTION_NOOP
        self._n_same_action: int = 0
        self._prev_snapshot: Optional[StateSnapshot] = None

        self.action_space = Discrete(N_ACTIONS)
        self.observation_space = DictSpace({
            "world":               Box(0, 3,   (_WS, _WS, _WS), dtype=np.int8),
            "player_pos":          Box(0, 4,   (3,),             dtype=np.int8),
            "player_dir":          Box(0, 3,   (1,),             dtype=np.int8),
            "inventory":           Box(0, 8,   (10, 2),          dtype=np.int8),
            "is_breaking":         Box(0, 1,   (1,),             dtype=np.int8),
            "break_progress_ratio":Box(0., 1., (1,),             dtype=np.float32),
        })

    # ── Gymnasium API ─────────────────────────────────────────────────────────

    def reset(
        self,
        *,
        seed: Optional[int] = None,
        options: Optional[dict[str, Any]] = None,
    ) -> tuple[dict, dict]:
        self._game.reset(seed=seed)
        self._player_id, self._player = self._game.world.create_player()
        self._prev_action = ACTION_NOOP
        self._n_same_action = 0
        self._prev_snapshot = take_snapshot(self._game.world, self._player)
        return self._observe(), {}

    def step(self, action: int) -> tuple[dict, float, bool, bool, dict]:
        action = int(action)
        assert self._player is not None
        before = self._prev_snapshot or take_snapshot(self._game.world, self._player)

        intent = self._action_to_intent(action)
        self._game.submit_player_intent(self._player_id, intent)
        self._game.tick()

        after = take_snapshot(self._game.world, self._player)  # player asserted above
        reward = compute_reward(
            before, after, action,
            self._prev_action, self._n_same_action,
            self._reward_cfg,
            action_noop=ACTION_NOOP,
        )

        # update action history
        if action == self._prev_action:
            self._n_same_action += 1
        else:
            self._n_same_action = 1
        self._prev_action   = action
        self._prev_snapshot = after

        obs       = self._observe()
        truncated = self._game.world.game_state.tick_count >= self._max_steps
        info      = {"tick": self._game.world.game_state.tick_count}
        return obs, reward, False, truncated, info

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _action_to_intent(self, action: int) -> BaseIntent:
        assert self._player is not None, "Player not initialized; did you forget to call reset()?"
        if action == ACTION_NOOP:
            return NoIntent()
        if action == ACTION_MOVE:
            return WalkIntent()
        if ACTION_TURN_EAST <= action <= ACTION_TURN_NORTH:
            return TurnIntent(direction=_DIRECTIONS[action - ACTION_TURN_EAST])
        if action == ACTION_PLACE_LOW:
            return self._place_intent(self._player.get_facing_block_position())
        if action == ACTION_PLACE_HIGH:
            return self._place_intent(self._player.get_facing_block_position_high())
        if action == ACTION_PLACE_DOWN:
            return self._place_intent(self._player.get_place_down_position())
        if action == ACTION_DIG_LOW:
            return DigIntent(target_position=self._player.get_facing_block_position())
        if action == ACTION_DIG_HIGH:
            return DigIntent(target_position=self._player.get_facing_block_position_high())
        if action == ACTION_DIG_DOWN:
            return DigIntent(target_position=self._player.get_position_below())
        if ACTION_SWAP_BASE <= action < ACTION_CRAFT_AXE:
            slot = action - ACTION_SWAP_BASE + 1
            return SwapInventoryIntent(slot1=0, slot2=slot)
        if action == ACTION_CRAFT_AXE:
            return CraftAxeIntent()
        return NoIntent()

    def _place_intent(self, position: Vec3I) -> BaseIntent:
        """Build a PlaceBlockIntent from the current main-hand item, or NoIntent."""
        assert self._player is not None, "Player not initialized; did you forget to call reset()?"
        main = self._player.main_hand_item
        if main is None:
            return NoIntent()
        block_type = _ITEM_TO_BLOCK.get(main.item_type)
        if block_type is None:
            return NoIntent()
        return PlaceBlockIntent(block_type, position)

    def _observe(self) -> dict[str, np.ndarray]:
        gs = self._game.world.game_state
        p  = self._player

        # World voxel grid
        world = np.zeros((_WS, _WS, _WS), dtype=np.int8)
        for (x, y, z), block in gs.blocks.items():
            world[x, y, z] = _BLOCK_ENCODE.get(block.block_type, 0)

        # Player position & direction
        player_pos = np.array([p.x, p.y, p.z], dtype=np.int8)
        player_dir = np.array([_DIR_ENCODE[p.direction]], dtype=np.int8)

        # Inventory: rows = slots, cols = [item_type_idx, count]
        inventory = np.zeros((10, 2), dtype=np.int8)
        for i, slot in enumerate(p.inventory):
            if slot.item and slot.item.count > 0:
                inventory[i, 0] = _ITEM_ENCODE.get(slot.item.item_type, 0)
                inventory[i, 1] = slot.item.count

        # Dig progress
        is_breaking = np.array([1 if p.breaking_block is not None else 0], dtype=np.int8)
        if p.breaking_block is not None and p.break_target_time > 0:
            ratio = np.float32(p.break_progress / p.break_target_time)
        else:
            ratio = np.float32(0.0)
        break_progress_ratio = np.array([ratio], dtype=np.float32)

        return {
            "world":                world,
            "player_pos":           player_pos,
            "player_dir":           player_dir,
            "inventory":            inventory,
            "is_breaking":          is_breaking,
            "break_progress_ratio": break_progress_ratio,
        }
