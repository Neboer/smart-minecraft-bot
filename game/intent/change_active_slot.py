from __future__ import annotations

from typing import TYPE_CHECKING

from game.mutation.base import MutationGroup, MutationGroupSequence
from game.mutation.change_active_slot import ChangeActiveSlotMutation
from .base import BaseIntent

if TYPE_CHECKING:
    from game.world import World


class ChangeActiveSlotIntent(BaseIntent):
    def __init__(self, slot: int) -> None:
        self.slot = slot

    @property
    def tick_cost(self) -> float:
        return 0.0

    def build_mutation_group_sequence(self, world: World, player_id: str) -> MutationGroupSequence:
        player = world.get_player(player_id)
        assert player is not None

        if not (0 <= self.slot < player.maximum_inventory_slots):
            return MutationGroupSequence(groups=[])

        return MutationGroupSequence(groups=[
            MutationGroup(
                mutations=[ChangeActiveSlotMutation(player_id, self.slot)],
                name=f"change_slot:{player_id}",
            )
        ])
