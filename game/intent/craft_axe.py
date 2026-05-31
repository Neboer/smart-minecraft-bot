from __future__ import annotations

from typing import TYPE_CHECKING

from game.core import ItemType
from game.mutation.base import MutationGroup, MutationGroupSequence
from game.mutation.abandon_dig import AbandonDigMutation
from game.mutation.craft_axe import CraftAxeMutation
from .base import BaseIntent

if TYPE_CHECKING:
    from game.world import World


class CraftAxeIntent(BaseIntent):
    def build_mutation_group_sequence(self, world: World, player_id: str) -> MutationGroupSequence:
        player = world.get_player(player_id)
        assert player is not None

        groups: list[MutationGroup] = []

        if player.breaking_block is not None:
            groups.append(MutationGroup(
                mutations=[AbandonDigMutation(player_id)],
                name=f"abandon:{player_id}",
            ))

        plank_count = sum(
            slot.item.count
            for slot in player.inventory
            if slot.item and slot.item.item_type == ItemType.PLANK
        )
        if plank_count < 3:
            return MutationGroupSequence(groups=groups)

        if not player.can_add_item_to_inventory(ItemType.WOODEN_AXE, 1):
            return MutationGroupSequence(groups=groups)

        groups.append(MutationGroup(
            mutations=[CraftAxeMutation(player_id)],
            name=f"craft_axe:{player_id}",
        ))
        return MutationGroupSequence(groups=groups)
