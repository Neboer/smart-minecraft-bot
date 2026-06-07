from __future__ import annotations

from collections import deque
from typing import Optional

from .core import Block, BlockType, GameState, Vec3I
from .data import (
    SAPLING_GROWTH_PROBABILITY,
    SAPLING_IDLE_PROBABILITY,
    SAPLING_TRUNK_HEIGHTS,
)
from .mutation.base import BaseMutation, MutationGroup, MutationGroupSequence, MutationSequence
from .mutation.sapling_growth import SaplingIdleGrowthMutation, SaplingGrowthMutation
from .player import Player


class World:
    def __init__(self) -> None:
        self.game_state = GameState()
        self.players: dict[str, Player] = {}
        self._player_counter = 0

    # ── Player management ────────────────────────────────────────────────────

    def create_player(self, player_id: Optional[str] = None) -> tuple[str, Player]:
        if player_id is None:
            self._player_counter += 1
            player_id = f"player_{self._player_counter}"
        player = Player(self.game_state)
        self.players[player_id] = player
        return player_id, player

    def get_player(self, player_id: str) -> Optional[Player]:
        return self.players.get(player_id)

    def remove_player(self, player_id: str) -> bool:
        if player_id in self.players:
            del self.players[player_id]
            return True
        return False

    # ── Position validation ──────────────────────────────────────────────────

    def is_position_valid(self, x: int, y: int, z: int) -> bool:
        ws = self.game_state.world_size
        return 0 <= x < ws and 0 <= y < ws and 0 <= z < ws

    # ── Player movement checks ───────────────────────────────────────────────

    def can_player_move_to(self, player: Player, target: Vec3I) -> bool:
        x, y, z = target
        if not self.is_position_valid(x, y, z):
            return False
        if y + player.height > self.game_state.world_size:
            return False
        for h in range(player.height):
            block = self.game_state.get_block(x, y + h, z)
            if block is not None and block.has_entity:
                return False
        return True

    def can_player_step_up_to(self, player: Player, target: Vec3I) -> bool:
        """Return True if the player can step up one block height to reach target.

        Requires a solid block directly below target (the step surface) and
        clear space at target and target+1 for player height.
        """
        x, y, z = target
        if not self.is_position_valid(x, y, z):
            return False
        if y + player.height > self.game_state.world_size:
            return False
        if y < 1:
            return False
        below = self.game_state.get_block(x, y - 1, z)
        if below is None or not below.has_entity:
            return False
        for h in range(player.height):
            block = self.game_state.get_block(x, y + h, z)
            if block is not None and block.has_entity:
                return False
        return True

    # ── Block placement validation ───────────────────────────────────────────

    def is_valid_place_position(self, player: Player, position: Vec3I, block_type: BlockType) -> bool:
        """Return True if position is a legal placement target for block_type.

        Valid positions are: facing, facing-high, or below the player.
        The player must be able to reach the position.
        """
        x, y, z = position
        if not self.is_position_valid(x, y, z):
            return False
        if self.game_state.get_block(x, y, z) is not None:
            return False
        if position == player.get_position():
            if block_type == BlockType.SAPLING:
                if y != 0:
                    return False
            else:
                above = Vec3I(player.x, player.y + player.height, player.z)
                if self.game_state.get_block(*above) is not None:
                    return False
        if not self.game_state.is_adjacent_to_block(x, y, z):
            return False
        return True

    # ── Tree growth conditions ───────────────────────────────────────────────

    def can_sapling_grow(self, position: Vec3I, trunk_height: int) -> bool:
        x, y, z = position
        if y != 0:
            return False
        sapling = self.game_state.get_block(x, y, z)
        if sapling is None or sapling.block_type != BlockType.SAPLING:
            return False
        neighbor_xz = {(x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1)}
        for other_pos in self.game_state.blocks:
            if other_pos == (x, y, z):
                continue
            ox, _, oz = other_pos
            if (ox, oz) == (x, z) or (ox, oz) in neighbor_xz:
                return False
        for height in range(trunk_height):
            b = self.game_state.get_block(x, y + height, z)
            if b is not None and b is not sapling:
                return False
        return self.game_state.get_block(x, y + trunk_height, z) is None

    # ── World mutation groups ────────────────────────────────────────────────

    def build_mutation_group_sequence(self) -> MutationGroupSequence:
        groups: list[MutationGroup] = []
        for pos, block in list(self.game_state.blocks.items()):
            if block.block_type != BlockType.SAPLING:
                continue
            vec_pos = Vec3I(*pos)
            if not self._can_attempt_tree_growth(vec_pos):
                continue
            groups.append(self._build_tree_growth_group(vec_pos))
        return MutationGroupSequence(groups=groups)

    def _can_attempt_tree_growth(self, position: Vec3I) -> bool:
        x, y, z = position
        if y != 0:
            return False
        sapling = self.game_state.get_block(x, y, z)
        if sapling is None or sapling.block_type != BlockType.SAPLING:
            return False
        neighbor_xz = {(x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1)}
        for other_pos in self.game_state.blocks:
            if other_pos == (x, y, z):
                continue
            ox, _, oz = other_pos
            if (ox, oz) == (x, z) or (ox, oz) in neighbor_xz:
                return False
        return True

    def _build_tree_growth_group(self, position: Vec3I) -> MutationGroup:
        per_height = SAPLING_GROWTH_PROBABILITY / len(SAPLING_TRUNK_HEIGHTS)
        mutations: list[BaseMutation] = [SaplingIdleGrowthMutation(position)]
        weights: list[float] = [SAPLING_IDLE_PROBABILITY]
        for trunk_height in SAPLING_TRUNK_HEIGHTS:
            mutations.append(SaplingGrowthMutation(position, trunk_height))
            weights.append(per_height)
        return MutationGroup(mutations=mutations, weights=weights, name=f"tree_growth:{position}")

    # ── Mutation execution ───────────────────────────────────────────────────

    def apply_mutation_sequence(self, sequence: MutationSequence) -> None:
        for mutation in sequence.mutations:
            if mutation.check_conditions(self):
                mutation.execute(self)

    # ── World state queries ──────────────────────────────────────────────────

    def get_world_state(self) -> dict[str, object]:
        blocks = [
            {"position": pos, "type": block.block_type.value, "has_entity": block.has_entity}
            for pos, block in self.game_state.blocks.items()
        ]
        players = {pid: p.get_state() for pid, p in self.players.items()}
        return {
            "tick": self.game_state.tick_count,
            "world_size": self.game_state.world_size,
            "blocks": blocks,
            "players": players,
        }

    def get_blocks_in_range(self, x: int, y: int, z: int, radius: int) -> list[dict[str, object]]:
        return [
            {"position": pos, "type": block.block_type.value, "has_entity": block.has_entity}
            for pos, block in self.game_state.blocks.items()
            if abs(pos[0] - x) <= radius and abs(pos[1] - y) <= radius and abs(pos[2] - z) <= radius
        ]

    def add_block(self, block_type: BlockType, x: int, y: int, z: int) -> bool:
        return self.game_state.add_block(Block(block_type, x, y, z))

    def remove_block(self, x: int, y: int, z: int) -> bool:
        return self.game_state.remove_block(x, y, z) is not None

    # ── Physics ──────────────────────────────────────────────────────────────

    def _player_has_support(self, player: Player) -> bool:
        if player.y <= 0:
            return True
        below = self.game_state.get_block(player.x, player.y - 1, player.z)
        return below is not None and below.has_entity

    def _can_fit_player_at(self, player: Player, x: int, y: int, z: int) -> bool:
        if x < 0 or y < 0 or z < 0:
            return False
        ws = self.game_state.world_size
        if x >= ws or y + player.height > ws or z >= ws:
            return False
        for h in range(player.height):
            block = self.game_state.get_block(x, y + h, z)
            if block is not None and block.has_entity:
                return False
        return True

    def _apply_gravity_to_player(self, player: Player) -> bool:
        changed = False
        while player.y > 0 and not self._player_has_support(player):
            player.y -= 1
            changed = True
        return changed

    def _clamp_player_to_bounds(self, player: Player) -> bool:
        ws = self.game_state.world_size
        max_y = max(0, ws - player.height)
        nx = min(max(player.x, 0), ws - 1)
        ny = min(max(player.y, 0), max_y)
        nz = min(max(player.z, 0), ws - 1)
        if (nx, ny, nz) != (player.x, player.y, player.z):
            player.x, player.y, player.z = nx, ny, nz
            return True
        return False

    def _resolve_player_collision(self, player: Player) -> bool:
        if self._can_fit_player_at(player, player.x, player.y, player.z):
            return False
        ws = self.game_state.world_size
        max_y = ws - player.height
        start = (player.x, player.y, player.z)
        visited = {start}
        queue: deque[tuple[int, int, int]] = deque([start])
        directions = [(0,0,1),(-1,0,0),(1,0,0),(0,-1,0),(0,1,0),(0,0,-1)]

        while queue:
            x, y, z = queue.popleft()
            if self._can_fit_player_at(player, x, y, z):
                player.x, player.y, player.z = x, y, z
                return True
            for dx, dy, dz in directions:
                nx, ny, nz = x + dx, y + dy, z + dz
                if nx < 0 or ny < 0 or nz < 0 or nx >= ws or ny > max_y or nz >= ws:
                    continue
                candidate = (nx, ny, nz)
                if candidate not in visited:
                    visited.add(candidate)
                    queue.append(candidate)

        raise RuntimeError(f"Unable to resolve collision for player at {start}")

    def is_world_legal(self) -> bool:
        ws = self.game_state.world_size
        for player in self.players.values():
            if not self._can_fit_player_at(player, player.x, player.y, player.z):
                return False
            if not self._player_has_support(player):
                return False
            if not (0 <= player.x < ws and 0 <= player.y < ws):
                return False
            if not (0 <= player.y <= ws - player.height):
                return False
        return True

    def do_physics(self, max_iterations: int = 32) -> None:
        for _ in range(max_iterations):
            changed = False
            for player in self.players.values():
                changed = self._apply_gravity_to_player(player) or changed
            for player in self.players.values():
                changed = self._resolve_player_collision(player) or changed
            for player in self.players.values():
                changed = self._clamp_player_to_bounds(player) or changed
            if not changed and self.is_world_legal():
                return
        raise RuntimeError("World physics failed to stabilize within the iteration limit")
