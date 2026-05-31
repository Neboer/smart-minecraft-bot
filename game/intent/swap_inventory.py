from __future__ import annotations

from typing import TYPE_CHECKING

from game.mutation.base import MutationGroup, MutationGroupSequence
from game.mutation.abandon_dig import AbandonDigMutation
from game.mutation.swap_inventory import SwapInventoryMutation
from .base import BaseIntent

if TYPE_CHECKING:
    from game.world import World


class SwapInventoryIntent(BaseIntent):
    def __init__(self, slot1: int, slot2: int) -> None:
        self.slot1 = slot1
        self.slot2 = slot2

    def build_mutation_group_sequence(self, world: World, player_id: str) -> MutationGroupSequence:
        player = world.get_player(player_id)
        assert player is not None

        groups: list[MutationGroup] = []

        if player.breaking_block is not None:
            groups.append(MutationGroup(
                mutations=[AbandonDigMutation(player_id)],
                name=f"abandon:{player_id}",
            ))

        n = player.maximum_inventory_slots
        if not (0 <= self.slot1 < n and 0 <= self.slot2 < n):
            return MutationGroupSequence(groups=groups)

        groups.append(MutationGroup(
            mutations=[SwapInventoryMutation(player_id, self.slot1, self.slot2)],
            name=f"swap:{player_id}",
        ))
        return MutationGroupSequence(groups=groups)
