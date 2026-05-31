from __future__ import annotations

from typing import TYPE_CHECKING

from .base import SinglePlayerBaseMutation

if TYPE_CHECKING:
    from game.world import World


class SwapInventoryMutation(SinglePlayerBaseMutation):
    def __init__(self, player_id: str, slot1: int, slot2: int) -> None:
        super().__init__(player_id, f"Swap slots {slot1}↔{slot2} for {player_id}")
        self.slot1 = slot1
        self.slot2 = slot2

    def check_conditions(self, world: World) -> bool:
        player = world.get_player(self.player_id)
        if player is None:
            return False
        n = player.maximum_inventory_slots
        return 0 <= self.slot1 < n and 0 <= self.slot2 < n

    def execute(self, world: World) -> None:
        player = world.get_player(self.player_id)
        assert player is not None
        inv = player.inventory
        inv[self.slot1].item, inv[self.slot2].item = inv[self.slot2].item, inv[self.slot1].item
