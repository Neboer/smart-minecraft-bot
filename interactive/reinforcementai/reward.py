"""Reward function for the smart-bot RL environment.

A snapshot of the relevant world/player state is taken before and after each
tick.  The reward is computed from the delta between the two snapshots plus
context about what action was taken and how many times it has been repeated.

Tunable weights live in RewardConfig — instantiate DEFAULT_CONFIG or create
your own and pass it to WorldGYM.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from game.core import BlockType, ItemType

if TYPE_CHECKING:
    from game.player import Player
    from game.world import World


# ── Config ────────────────────────────────────────────────────────────────────

@dataclass
class RewardConfig:
    # Penalty when a non-noop action caused zero observable change
    no_effect: float     = -1.0
    # Penalty when a non-noop action caused zero world change (even if player state changed, e.g. moved into a wall)
    no_world_change: float = -0.5

    # Small per-tick cost for choosing noop (encourages purposeful waiting)
    noop_idle: float     = -0.1

    # Reward for start digging on a new non-sapling block (encouragement to dig, but not saplings which are renewable)
    dig_start: float     =  1.0

    # Reward for continuing to dig the same block (focus encouragement)
    dig_progress: float  =  0.3

    # Penalty for abandoning a dig (switching breaking_block)
    dig_abandon: float   = -5.0

    # Reward when a non-sapling block is removed from the world
    block_broken_base: float    =  5.0
    plank_broken_bonus: float   = 10.0   # on top of base
    leaf_broken_bonus: float    =  2.0   # on top of base
    sapling_broken_penalty: float = -10.0  # on top of base (negative)

    # Reward per new plank block appearing in world (tree grew)
    plank_in_world: float       =  2.0

    # Reward per new sapling placed in world
    sapling_placed: float       =  1.0

    # Inventory rewards
    plank_in_inv: float         =  8.0   # per plank collected
    sapling_inv_base: float     =  4.0   # per sapling collected (before diminishing)
    sapling_saturation: int     = 12     # inventory saplings at which reward → 0

    # Movement when not digging
    move_free: float            =  0.1

    # Penalty for repeating the same non-noop action while not digging
    repeat_penalty: float       = -0.3
    repeat_threshold: int       =  3     # consecutive same-action count to trigger

# Singleton default — override in WorldGYM init if needed
DEFAULT_CONFIG = RewardConfig()


# ── State snapshot ────────────────────────────────────────────────────────────

@dataclass
class StateSnapshot:
    """Compact view of game state used for reward computation."""
    # {(x,y,z): BlockType} — for change detection
    blocks: dict[tuple[int,int,int], BlockType] = field(default_factory=dict)
    # per-type block counts
    block_counts: dict[BlockType, int]          = field(default_factory=dict)
    # player
    pos: tuple[int,int,int]  = (0, 0, 0)
    dir_idx: int             = 0
    breaking_block: tuple[int,int,int] | None = None
    # inventory item totals
    inv: dict[ItemType, int] = field(default_factory=dict)


def take_snapshot(world: World, player: Player) -> StateSnapshot:
    """Capture a StateSnapshot from the current game state."""
    gs = world.game_state

    blocks: dict[tuple[int,int,int], BlockType] = {
        pos: blk.block_type for pos, blk in gs.blocks.items()
    }
    block_counts: dict[BlockType, int] = {}
    for bt in blocks.values():
        block_counts[bt] = block_counts.get(bt, 0) + 1

    inv: dict[ItemType, int] = {}
    for slot in player.inventory:
        if slot.item and slot.item.count > 0:
            inv[slot.item.item_type] = inv.get(slot.item.item_type, 0) + slot.item.count

    breaking = (
        tuple(player.breaking_block)
        if player.breaking_block is not None
        else None
    )

    return StateSnapshot(
        blocks       = blocks,
        block_counts = block_counts,
        pos          = (player.x, player.y, player.z),
        dir_idx      = player.direction.value[0],   # use x-component as proxy
        breaking_block = breaking,
        inv          = inv,
    )


# ── Reward computation ────────────────────────────────────────────────────────

def compute_reward(
    before: StateSnapshot,
    after:  StateSnapshot,
    action: int,
    prev_action: int,
    n_same_action: int,
    cfg: RewardConfig = DEFAULT_CONFIG,
    *,
    action_noop: int = 0,
) -> float:
    """Return a scalar reward given before/after snapshots and action context."""
    r = 0.0

    # ── 1. No-effect penalty ─────────────────────────────────────────────────
    if action == action_noop:
        r += cfg.noop_idle
    else:
        unchanged = (
            before.blocks        == after.blocks
            and before.pos       == after.pos
            and before.dir_idx   == after.dir_idx
            and before.breaking_block == after.breaking_block
            and before.inv       == after.inv
        )
        if unchanged:
            r += cfg.no_effect
        else:
            # Check if the action caused any world changes (excluding saplings)
            world_changed = (
                before.blocks != after.blocks
                or before.breaking_block != after.breaking_block
            )
            if not world_changed:
                r += cfg.no_world_change

    # ── 2. Dig-progress reward ───────────────────────────────────────────────
    if (
        after.breaking_block is not None
        and after.breaking_block == before.breaking_block
    ):
        r += cfg.dig_progress
    
    if (
        before.breaking_block is None
        and after.breaking_block is not None
    ):
        r += cfg.dig_start

    # ── 3. Blocks broken ─────────────────────────────────────────────────────
    for pos, bt in before.blocks.items():
        if pos not in after.blocks:
            r += cfg.block_broken_base
            if bt == BlockType.PLANK:
                r += cfg.plank_broken_bonus
            elif bt == BlockType.LEAF:
                r += cfg.leaf_broken_bonus
            elif bt == BlockType.SAPLING:
                r += cfg.sapling_broken_penalty

    # abandon-dig penalty (if switched breaking_block since last tick)
    if (
        before.breaking_block is not None
        and after.breaking_block != before.breaking_block
    ):
        r += cfg.dig_abandon
    
    # ── 4. New plank blocks in world (tree grew) ─────────────────────────────
    delta_world_planks = (
        after.block_counts.get(BlockType.PLANK, 0)
        - before.block_counts.get(BlockType.PLANK, 0)
    )
    if delta_world_planks > 0:
        r += delta_world_planks * cfg.plank_in_world

    # ── 5. Saplings placed in world ──────────────────────────────────────────
    delta_world_sapling = (
        after.block_counts.get(BlockType.SAPLING, 0)
        - before.block_counts.get(BlockType.SAPLING, 0)
    )
    if delta_world_sapling > 0:
        r += delta_world_sapling * cfg.sapling_placed

    # ── 6. Inventory: planks gained ──────────────────────────────────────────
    delta_inv_planks = (
        after.inv.get(ItemType.PLANK, 0)
        - before.inv.get(ItemType.PLANK, 0)
    )
    if delta_inv_planks > 0:
        r += delta_inv_planks * cfg.plank_in_inv

    # ── 7. Inventory: saplings gained (diminishing) ──────────────────────────
    delta_inv_sapling = (
        after.inv.get(ItemType.SAPLING, 0)
        - before.inv.get(ItemType.SAPLING, 0)
    )
    if delta_inv_sapling > 0:
        current_saplings = after.inv.get(ItemType.SAPLING, 0)
        # Linear diminishing: reward → 0 as inventory approaches saturation
        factor = max(0.0, 1.0 - current_saplings / cfg.sapling_saturation)
        r += delta_inv_sapling * cfg.sapling_inv_base * factor

    # ── 8. Free-movement reward ──────────────────────────────────────────────
    if after.breaking_block is None and before.pos != after.pos:
        r += cfg.move_free

    # ── 9. Repeat-action penalty (when not digging) ──────────────────────────
    if (
        after.breaking_block is None
        and action != action_noop
        and action == prev_action
        and n_same_action >= cfg.repeat_threshold
    ):
        r += cfg.repeat_penalty

    return r
