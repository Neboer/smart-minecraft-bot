from __future__ import annotations

from typing import TYPE_CHECKING

from game.core import Vec3I
from game.mutation.base import MutationGroup, MutationGroupSequence
from game.mutation.abandon_dig import AbandonDigMutation
from game.mutation.move_player import MovePlayerMutation
from game.mutation.no_op import NoOpMutation
from .base import BaseIntent

if TYPE_CHECKING:
    from game.world import World


class WalkIntent(BaseIntent):
    """Move one step in the player's current facing direction.

    If a solid block is directly in front at the same height, the player
    automatically steps up one block (1 tick, same as walking on flat ground).
    """

    def build_mutation_group_sequence(self, world: World, player_id: str) -> MutationGroupSequence:
        player = world.get_player(player_id)
        assert player is not None

        groups: list[MutationGroup] = []

        if player.breaking_block is not None:
            groups.append(MutationGroup(
                mutations=[AbandonDigMutation(player_id)],
                name=f"abandon:{player_id}",
            ))

        dx, _, dz = player.direction.value
        same_level = Vec3I(player.x + dx, player.y, player.z + dz)
        step_up = Vec3I(player.x + dx, player.y + 1, player.z + dz)

        if world.can_player_move_to(player, same_level):
            target = same_level
        elif world.can_player_step_up_to(player, step_up):
            target = step_up
        else:
            groups.append(MutationGroup(
                mutations=[NoOpMutation(f"walk_blocked:{player_id}")],
                name=f"walk_blocked:{player_id}",
            ))
            return MutationGroupSequence(groups=groups)

        groups.append(MutationGroup(
            mutations=[MovePlayerMutation(player_id, target)],
            name=f"move:{player_id}",
        ))
        return MutationGroupSequence(groups=groups)
