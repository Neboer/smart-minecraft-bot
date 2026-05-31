from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from game.core import BlockType, ItemType, Vec3I
from game.data import AXE_BREAK_MULTIPLIER, BLOCK_BREAK_TIME, BLOCK_DROP_OPTIONS
from game.mutation.base import BaseMutation, MutationGroup, MutationGroupSequence
from game.mutation.begin_dig import BeginDigMutation
from game.mutation.continue_dig import ContinueDigMutation
from game.mutation.finish_dig import FinishDigMutation
from .base import BaseIntent

if TYPE_CHECKING:
    from game.world import World


class DigIntent(BaseIntent):
    def __init__(self, target_position: Optional[tuple[int, int, int]] = None) -> None:
        self.target_position: Vec3I | None = (
            Vec3I(*target_position) if target_position is not None else None
        )

    def build_mutation_group_sequence(self, world: World, player_id: str) -> MutationGroupSequence:
        player = world.get_player(player_id)
        assert player is not None

        target = self.target_position or player.breaking_block
        if target is None:
            return MutationGroupSequence(groups=[])

        if not world.is_position_valid(target.x, target.y, target.z):
            return MutationGroupSequence(groups=[])

        if not player.can_reach_position(target):
            return MutationGroupSequence(groups=[])

        block = world.game_state.get_block(*target)
        if block is None:
            return MutationGroupSequence(groups=[])

        # ── Ongoing dig (block already started) ──────────────────────────────
        if player.breaking_block == target and player.break_target_time > 0.0:
            if player.break_progress + 1.0 >= player.break_target_time:
                drop_options = BLOCK_DROP_OPTIONS[block.block_type]
                mutations: list[BaseMutation] = [
                    FinishDigMutation(
                        player_id=player_id,
                        target=target,
                        drop_item_type=item_type,
                        drop_count=count,
                    )
                    for count, _, item_type in drop_options
                ]
                weights: list[float] = [prob for _, prob, _ in drop_options]
                return MutationGroupSequence(groups=[
                    MutationGroup(mutations=mutations, weights=weights, name=f"dig_finish:{player_id}")
                ])
            else:
                return MutationGroupSequence(groups=[
                    MutationGroup(
                        mutations=[ContinueDigMutation(player_id, target)],
                        name=f"dig_continue:{player_id}",
                    )
                ])

        # ── New dig ───────────────────────────────────────────────────────────
        # The begin tick counts as 1 unit of work. We emit Begin as the first
        # group and Finish (if break_time ≤ 1) or Continue as the second group,
        # both executing in the same tick so a 1-tick block breaks immediately.
        break_time = BLOCK_BREAK_TIME[block.block_type]
        if (
            player.main_hand_item is not None
            and player.main_hand_item.item_type == ItemType.WOODEN_AXE
            and block.block_type == BlockType.PLANK
        ):
            break_time *= AXE_BREAK_MULTIPLIER

        drop_options = BLOCK_DROP_OPTIONS[block.block_type]
        groups: list[MutationGroup] = [
            MutationGroup(
                mutations=[BeginDigMutation(player_id, target, break_time)],
                name=f"dig_begin:{player_id}",
            )
        ]

        # Second group: finish if break_time ≤ 1 (single-tick block), else continue.
        if break_time <= 1.0:
            finish_mutations: list[BaseMutation] = [
                FinishDigMutation(
                    player_id=player_id,
                    target=target,
                    drop_item_type=item_type,
                    drop_count=count,
                )
                for count, _, item_type in drop_options
            ]
            finish_weights: list[float] = [prob for _, prob, _ in drop_options]
            groups.append(MutationGroup(
                mutations=finish_mutations, weights=finish_weights,
                name=f"dig_finish:{player_id}",
            ))
        else:
            groups.append(MutationGroup(
                mutations=[ContinueDigMutation(player_id, target)],
                name=f"dig_continue:{player_id}",
            ))

        return MutationGroupSequence(groups=groups)
