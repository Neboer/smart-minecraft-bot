from __future__ import annotations

from typing import TYPE_CHECKING

from game.core import Block, BlockType, Vec3I
from .base import BaseMutation

if TYPE_CHECKING:
    from game.world import World


class SaplingIdleGrowthMutation(BaseMutation):
    def __init__(self, position: Vec3I) -> None:
        super().__init__(f"Sapling at {position} stays")
        self.position = position

    def check_conditions(self, world: World) -> bool:
        block = world.game_state.get_block(*self.position)
        return block is not None and block.block_type == BlockType.SAPLING

    def execute(self, world: World) -> None:
        pass


class SaplingGrowthMutation(BaseMutation):
    def __init__(self, position: Vec3I, trunk_height: int) -> None:
        super().__init__(f"Sapling at {position} grows to height {trunk_height}")
        self.position = position
        self.trunk_height = trunk_height

    def check_conditions(self, world: World) -> bool:
        return world.can_sapling_grow(self.position, self.trunk_height)

    def execute(self, world: World) -> None:
        x, y, z = self.position
        world.game_state.remove_block(x, y, z)
        for height in range(self.trunk_height):
            world.game_state.add_block(Block(BlockType.PLANK, x, y, z + height))
        world.game_state.add_block(Block(BlockType.LEAF, x, y, z + self.trunk_height))
