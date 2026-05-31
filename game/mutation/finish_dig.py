from __future__ import annotations

from typing import TYPE_CHECKING

from game.core import ItemType, Vec3I
from .base import SinglePlayerBaseMutation

if TYPE_CHECKING:
    from game.world import World


class FinishDigMutation(SinglePlayerBaseMutation):
    def __init__(
        self,
        player_id: str,
        target: Vec3I,
        drop_item_type: ItemType,
        drop_count: int,
    ) -> None:
        super().__init__(
            player_id,
            f"Finish dig {target} → x{drop_count} {drop_item_type.value}",
        )
        self.target = target
        self.drop_item_type = drop_item_type
        self.drop_count = drop_count

    def check_conditions(self, world: World) -> bool:
        player = world.get_player(self.player_id)
        if player is None:
            return False
        if world.game_state.get_block(*self.target) is None:
            return False
        if player.breaking_block != self.target:
            return False
        if player.break_progress + 1.0 < player.break_target_time:
            return False
        return player.can_add_item_to_inventory(self.drop_item_type, self.drop_count)

    def execute(self, world: World) -> None:
        player = world.get_player(self.player_id)
        assert player is not None
        block = world.game_state.remove_block(*self.target)
        if block is None:
            return
        player.add_item_to_inventory(self.drop_item_type, self.drop_count)
        player.breaking_block = None
        player.break_progress = 0.0
        player.break_target_time = 0.0
