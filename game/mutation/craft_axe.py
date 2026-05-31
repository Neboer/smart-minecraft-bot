from __future__ import annotations

from typing import TYPE_CHECKING

from game.core import ItemType
from .base import SinglePlayerBaseMutation

if TYPE_CHECKING:
    from game.world import World


class CraftAxeMutation(SinglePlayerBaseMutation):
    def __init__(self, player_id: str) -> None:
        super().__init__(player_id, f"Craft wooden axe for {player_id}")

    def check_conditions(self, world: World) -> bool:
        player = world.get_player(self.player_id)
        if player is None:
            return False
        plank_count = sum(
            slot.item.count
            for slot in player.inventory
            if slot.item and slot.item.item_type == ItemType.PLANK
        )
        return plank_count >= 3 and player.can_add_item_to_inventory(ItemType.WOODEN_AXE, 1)

    def execute(self, world: World) -> None:
        player = world.get_player(self.player_id)
        assert player is not None
        remaining = 3
        for slot in player.inventory:
            if remaining <= 0:
                break
            if slot.item and slot.item.item_type == ItemType.PLANK:
                to_remove = min(remaining, slot.item.count)
                slot.item.count -= to_remove
                remaining -= to_remove
                if slot.item.count <= 0:
                    slot.item = None
        player.add_item_to_inventory(ItemType.WOODEN_AXE, 1)
