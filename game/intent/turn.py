from __future__ import annotations

from typing import TYPE_CHECKING

from game.core import Direction
from game.mutation.base import MutationGroup, MutationGroupSequence
from game.mutation.abandon_dig import AbandonDigMutation
from game.mutation.turn_player import TurnPlayerMutation
from .base import BaseIntent

if TYPE_CHECKING:
    from game.world import World


class TurnIntent(BaseIntent):
    @property
    def tick_cost(self) -> float:
        return 0.0

    def __init__(self, direction: Direction | str) -> None:
        if isinstance(direction, str):
            self.direction = Direction.from_name(direction)
        else:
            self.direction = direction

    def build_mutation_group_sequence(self, world: World, player_id: str) -> MutationGroupSequence:
        player = world.get_player(player_id)
        assert player is not None

        groups: list[MutationGroup] = []

        if player.breaking_block is not None:
            groups.append(MutationGroup(
                mutations=[AbandonDigMutation(player_id)],
                name=f"abandon:{player_id}",
            ))

        groups.append(MutationGroup(
            mutations=[TurnPlayerMutation(player_id, self.direction)],
            name=f"turn:{player_id}",
        ))
        return MutationGroupSequence(groups=groups)
