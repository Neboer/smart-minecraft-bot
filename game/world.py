from __future__ import annotations

from collections import deque
from typing import Any, Dict, List, Optional, Tuple

from .core import Block, BlockType, GameState
from .mutations import (
    Mutation,
    MutationGroup,
    MutationSequence,
    MutationGroupSequence,
    build_tree_growth_mutation_group,
)
from .player import Player


class World:
    def __init__(self):
        self.game_state = GameState()
        self.players: Dict[str, Player] = {}
        self.player_counter = 0

    def create_player(self, player_id: Optional[str] = None) -> Tuple[str, Player]:
        """Create a new player in the world."""
        if player_id is None:
            self.player_counter += 1
            player_id = f"player_{self.player_counter}"

        player = Player(self.game_state)
        self.players[player_id] = player
        return player_id, player

    def get_player(self, player_id: str) -> Optional[Player]:
        """Get a player by ID."""
        return self.players.get(player_id)

    def remove_player(self, player_id: str) -> bool:
        """Remove a player from the world."""
        if player_id in self.players:
            del self.players[player_id]
            return True
        return False

    def build_mutation_group_sequence(self) -> MutationGroupSequence:
        """Build the natural world mutation space for one tick.

        This method must not mutate world state.
        """
        groups: List[MutationGroup] = []
        groups.extend(self._build_tree_growth_mutation_groups())
        return MutationGroupSequence(groups=groups)

    def _build_tree_growth_mutation_groups(self) -> List[MutationGroup]:
        groups: List[MutationGroup] = []
        saplings = [
            pos
            for pos, block in self.game_state.blocks.items()
            if block.block_type == BlockType.SAPLING
        ]

        for pos in saplings:
            if not self._can_attempt_tree_growth(pos):
                continue
            groups.append(build_tree_growth_mutation_group(pos))

        return groups

    def _can_attempt_tree_growth(self, position: Tuple[int, int, int]) -> bool:
        x, y, z = position
        if z != 0:
            return False

        sapling = self.game_state.get_block(x, y, z)
        if sapling is None or sapling.block_type != BlockType.SAPLING:
            return False

        neighbor_xy = {(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)}
        for other_pos in self.game_state.blocks.keys():
            if other_pos == position:
                continue
            ox, oy, oz = other_pos
            if (ox, oy) == (x, y):
                return False
            if (ox, oy) in neighbor_xy:
                return False

        return True

    def apply_mutation_sequence(self, sequence: MutationSequence | List[Mutation]) -> Dict[str, Any]:
        """Execute a sampled mutation sequence against the world."""
        if isinstance(sequence, list):
            sequence = MutationSequence(mutations=sequence)

        results: List[Dict[str, Any]] = []
        for mutation in sequence.mutations:
            result = mutation.execute(self)
            results.append(
                {
                    "mutation": mutation.to_dict(),
                    "result": result,
                }
            )

        return {
            "probability": sequence.probability,
            "results": results,
        }

    def execute_mutation_sequence(self, sequence: MutationSequence | List[Mutation]) -> Dict[str, Any]:
        """Backward-compatible alias for apply_mutation_sequence()."""
        return self.apply_mutation_sequence(sequence)

    def get_world_state(self) -> Dict[str, Any]:
        """Get the entire world state."""
        blocks = []
        for (x, y, z), block in self.game_state.blocks.items():
            blocks.append(
                {
                    "position": (x, y, z),
                    "type": block.block_type.value,
                    "has_entity": block.has_entity,
                }
            )

        players = {}
        for player_id, player in self.players.items():
            players[player_id] = player.get_state()

        return {
            "tick": self.game_state.tick_count,
            "world_size": self.game_state.world_size,
            "blocks": blocks,
            "players": players,
        }

    def get_blocks_in_range(self, x: int, y: int, z: int, radius: int) -> List[Dict[str, Any]]:
        """Get all blocks within a certain radius of a position."""
        result = []
        for (bx, by, bz), block in self.game_state.blocks.items():
            if abs(bx - x) <= radius and abs(by - y) <= radius and abs(bz - z) <= radius:
                result.append(
                    {
                        "position": (bx, by, bz),
                        "type": block.block_type.value,
                        "has_entity": block.has_entity,
                    }
                )
        return result

    def add_block(self, block_type: BlockType, x: int, y: int, z: int) -> bool:
        """Add a block to the world (for testing or admin purposes)."""
        block = Block(block_type, x, y, z)
        return self.game_state.add_block(block)

    def remove_block(self, x: int, y: int, z: int) -> bool:
        """Remove a block from the world (for testing or admin purposes)."""
        block = self.game_state.remove_block(x, y, z)
        return block is not None

    def _player_support_is_valid(self, player: Player) -> bool:
        if player.z <= 0:
            return True
        below = self.game_state.get_block(player.x, player.y, player.z - 1)
        return below is not None and below.has_entity

    def _can_fit_player_at(self, player: Player, x: int, y: int, z: int) -> bool:
        if x < 0 or y < 0 or z < 0:
            return False
        if x >= self.game_state.world_size or y >= self.game_state.world_size:
            return False
        if z + player.height > self.game_state.world_size:
            return False

        for height in range(player.height):
            block = self.game_state.get_block(x, y, z + height)
            if block is not None and block.has_entity:
                return False
        return True

    def _apply_gravity_to_player(self, player: Player) -> bool:
        changed = False
        while player.z > 0 and not self._player_support_is_valid(player):
            player.z -= 1
            changed = True
        return changed

    def _clamp_player_to_bounds(self, player: Player) -> bool:
        changed = False
        max_bottom_z = max(0, self.game_state.world_size - player.height)

        new_x = min(max(player.x, 0), self.game_state.world_size - 1)
        new_y = min(max(player.y, 0), self.game_state.world_size - 1)
        new_z = min(max(player.z, 0), max_bottom_z)

        if (new_x, new_y, new_z) != (player.x, player.y, player.z):
            player.x, player.y, player.z = new_x, new_y, new_z
            changed = True
        return changed

    def _resolve_player_collision(self, player: Player) -> bool:
        if self._can_fit_player_at(player, player.x, player.y, player.z):
            return False

        max_x = self.game_state.world_size - 1
        max_y = self.game_state.world_size - 1
        max_z = self.game_state.world_size - player.height

        start = (player.x, player.y, player.z)
        visited = {start}
        queue = deque([start])
        directions = [
            (0, 0, 1),
            (-1, 0, 0),
            (1, 0, 0),
            (0, -1, 0),
            (0, 1, 0),
            (0, 0, -1),
        ]

        while queue:
            x, y, z = queue.popleft()
            if self._can_fit_player_at(player, x, y, z):
                player.x, player.y, player.z = x, y, z
                return True

            for dx, dy, dz in directions:
                nx, ny, nz = x + dx, y + dy, z + dz
                if nx < 0 or ny < 0 or nz < 0:
                    continue
                if nx > max_x or ny > max_y or nz > max_z:
                    continue
                candidate = (nx, ny, nz)
                if candidate in visited:
                    continue
                visited.add(candidate)
                queue.append(candidate)

        raise RuntimeError(f"Unable to resolve collision for player at {start}")

    def is_world_legal(self) -> bool:
        for player in self.players.values():
            if not self._can_fit_player_at(player, player.x, player.y, player.z):
                return False
            if not self._player_support_is_valid(player):
                return False
            if not (0 <= player.x < self.game_state.world_size):
                return False
            if not (0 <= player.y < self.game_state.world_size):
                return False
            if not (0 <= player.z <= self.game_state.world_size - player.height):
                return False
        return True

    def do_physics(self, max_iterations: int = 32) -> Dict[str, Any]:
        """Deterministically stabilize the world after a tick.

        The routine repeatedly applies gravity, collision resolution, and
        boundary squeezing until the world becomes legal or the iteration cap
        is reached.
        """
        iterations = 0
        while iterations < max_iterations:
            changed = False

            for player in self.players.values():
                changed = self._apply_gravity_to_player(player) or changed

            for player in self.players.values():
                changed = self._resolve_player_collision(player) or changed

            for player in self.players.values():
                changed = self._clamp_player_to_bounds(player) or changed

            iterations += 1
            if not changed and self.is_world_legal():
                return {
                    "success": True,
                    "iterations": iterations,
                    "stabilized": True,
                }

        raise RuntimeError("World physics failed to stabilize within the iteration limit")
