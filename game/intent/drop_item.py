from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from game.mutation.base import MutationGroup, MutationGroupSequence
from game.mutation.abandon_dig import AbandonDigMutation
from game.mutation.drop_item import DropOneMutation, DropStackMutation
from .base import BaseIntent

if TYPE_CHECKING:
    from game.world import World


class DropOneIntent(BaseIntent):
    def __init__(self, slot: Optional[int] = None) -> None:
        self.slot = slot

    def build_mutation_group_sequence(self, world: World, player_id: str) -> MutationGroupSequence:
        player = world.get_player(player_id)
        assert player is not None

        groups: list[MutationGroup] = []

        if player.breaking_block is not None:
            groups.append(MutationGroup(
                mutations=[AbandonDigMutation(player_id)],
                name=f"abandon:{player_id}",
            ))

        slot = self.slot if self.slot is not None else player.main_hand_slot
        groups.append(MutationGroup(
            mutations=[DropOneMutation(player_id, slot)],
            name=f"drop_one:{player_id}",
        ))
        return MutationGroupSequence(groups=groups)


class DropStackIntent(BaseIntent):
    def __init__(self, slot: Optional[int] = None) -> None:
        self.slot = slot

    def build_mutation_group_sequence(self, world: World, player_id: str) -> MutationGroupSequence:
        player = world.get_player(player_id)
        assert player is not None

        groups: list[MutationGroup] = []

        if player.breaking_block is not None:
            groups.append(MutationGroup(
                mutations=[AbandonDigMutation(player_id)],
                name=f"abandon:{player_id}",
            ))

        slot = self.slot if self.slot is not None else player.main_hand_slot
        groups.append(MutationGroup(
            mutations=[DropStackMutation(player_id, slot)],
            name=f"drop_stack:{player_id}",
        ))
        return MutationGroupSequence(groups=groups)
