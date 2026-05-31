from __future__ import annotations

from typing import TYPE_CHECKING

from game.mutation.base import MutationGroup, MutationGroupSequence
from game.mutation.abandon_dig import AbandonDigMutation
from game.mutation.no_op import NoOpMutation
from .base import BaseIntent

if TYPE_CHECKING:
    from game.world import World


class NoIntent(BaseIntent):
    @property
    def tick_cost(self) -> float:
        return 0.0

    def build_mutation_group_sequence(self, world: World, player_id: str) -> MutationGroupSequence:
        player = world.get_player(player_id)
        assert player is not None

        if player.breaking_block is not None:
            return MutationGroupSequence(groups=[
                MutationGroup(
                    mutations=[AbandonDigMutation(player_id)],
                    name=f"abandon:{player_id}",
                )
            ])

        return MutationGroupSequence(groups=[
            MutationGroup(
                mutations=[NoOpMutation(f"no_intent:{player_id}")],
                name=f"noop:{player_id}",
            )
        ])
