from __future__ import annotations

from typing import TYPE_CHECKING

from game.core import BlockType, Vec3I
from game.mutation.base import MutationGroup, MutationGroupSequence
from game.mutation.abandon_dig import AbandonDigMutation
from game.mutation.place_block import PlaceBlockMutation
from .base import BaseIntent

if TYPE_CHECKING:
    from game.world import World


class PlaceBlockIntent(BaseIntent):
    """Place a block of block_type at the player-specified position.

    position must be one of the three reachable positions:
      - player.get_facing_block_position()
      - player.get_facing_block_position_high()
      - player.get_position_below()
    """

    def __init__(self, block_type: BlockType, position: Vec3I) -> None:
        self.block_type = block_type
        self.position = Vec3I(*position) if not isinstance(position, Vec3I) else position

    def build_mutation_group_sequence(self, world: World, player_id: str) -> MutationGroupSequence:
        player = world.get_player(player_id)
        assert player is not None

        groups: list[MutationGroup] = []

        if player.breaking_block is not None:
            groups.append(MutationGroup(
                mutations=[AbandonDigMutation(player_id)],
                name=f"abandon:{player_id}",
            ))

        main_hand = player.main_hand_item
        if main_hand is None or main_hand.item_type != self.block_type.to_item_type():
            return MutationGroupSequence(groups=groups)

        if not player.can_reach_position(self.position):
            return MutationGroupSequence(groups=groups)

        if not world.is_valid_place_position(player, self.position, self.block_type):
            return MutationGroupSequence(groups=groups)

        groups.append(MutationGroup(
            mutations=[PlaceBlockMutation(player_id, self.block_type, self.position)],
            name=f"place:{player_id}",
        ))
        return MutationGroupSequence(groups=groups)
