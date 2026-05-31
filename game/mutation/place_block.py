from __future__ import annotations

from typing import TYPE_CHECKING

from game.core import Block, BlockType, Vec3I
from .base import SinglePlayerBaseMutation

if TYPE_CHECKING:
    from game.world import World


class PlaceBlockMutation(SinglePlayerBaseMutation):
    def __init__(self, player_id: str, block_type: BlockType, position: Vec3I) -> None:
        super().__init__(player_id, f"Place {block_type.value} at {position}")
        self.block_type = block_type
        self.position = position

    def check_conditions(self, world: World) -> bool:
        player = world.get_player(self.player_id)
        if player is None:
            return False
        if not world.is_valid_place_position(player, self.position, self.block_type):
            return False
        main_hand = player.main_hand_item
        return main_hand is not None and main_hand.item_type == self.block_type.to_item_type()

    def execute(self, world: World) -> None:
        player = world.get_player(self.player_id)
        assert player is not None
        world.game_state.add_block(Block(self.block_type, *self.position))
        main_hand_item = player.inventory[player.main_hand_slot].item
        if main_hand_item is not None:
            main_hand_item.count -= 1
            if main_hand_item.count <= 0:
                player.inventory[player.main_hand_slot].item = None
