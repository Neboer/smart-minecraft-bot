from __future__ import annotations

from typing import TYPE_CHECKING

from .base import SinglePlayerBaseMutation

if TYPE_CHECKING:
    from game.world import World


class ChangeActiveSlotMutation(SinglePlayerBaseMutation):
    def __init__(self, player_id: str, slot: int) -> None:
        super().__init__(player_id, f"Change active slot to {slot} for {player_id}")
        self.slot = slot

    def check_conditions(self, world: World) -> bool:
        player = world.get_player(self.player_id)
        return player is not None and 0 <= self.slot < player.maximum_inventory_slots

    def execute(self, world: World) -> None:
        player = world.get_player(self.player_id)
        assert player is not None
        player._active_slot = self.slot
