from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .core import BlockType, ItemType
from .mutations import (
    PlayerWarning,
    MutationGroupSequence,
    build_abandon_dig_group,
    build_craft_axe_group,
    build_dig_continue_group,
    build_dig_finish_group,
    build_dig_progress_group,
    build_move_group,
    build_place_group,
    build_swap_inventory_group,
    build_turn_group,
    NoOpMutation,
    MutationGroup,
)
from .mutations import _coerce_direction  # re-used for validation


@dataclass
class PlayerIntent:
    """Base player intent.

    Every intent resolves against the current world state and returns a
    MutationGroupSequence plus any PlayerWarnings generated during validation.
    """

    def build_mutation_group_sequence(self, world: Any, player_id: str) -> Tuple[MutationGroupSequence, List[PlayerWarning]]:
        raise NotImplementedError

    def to_mutation_group_sequence(self, world: Any, player_id: str) -> Tuple[MutationGroupSequence, List[PlayerWarning]]:
        return self.build_mutation_group_sequence(world, player_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent_type": self.__class__.__name__,
            "parameters": {
                key: value for key, value in self.__dict__.items()
            },
        }


@dataclass
class NoIntent(PlayerIntent):
    def build_mutation_group_sequence(self, world: Any, player_id: str) -> Tuple[MutationGroupSequence, List[PlayerWarning]]:
        player = world.get_player(player_id)
        if player is None:
            return MutationGroupSequence(groups=[]), [
                PlayerWarning(player_id=player_id, code="PLAYER_MISSING", message=f"Player {player_id} not found")
            ]

        if player.breaking_block is not None:
            return MutationGroupSequence(groups=[build_abandon_dig_group(player_id=player_id)]), []

        return MutationGroupSequence(
            groups=[
                MutationGroup(
                    mutations=[NoOpMutation(description=f"No intent for {player_id}")],
                    name=f"no_intent:{player_id}",
                )
            ]
        ), []


@dataclass
class WalkIntent(PlayerIntent):
    def build_mutation_group_sequence(self, world: Any, player_id: str) -> Tuple[MutationGroupSequence, List[PlayerWarning]]:
        player = world.get_player(player_id)
        if player is None:
            return MutationGroupSequence(groups=[]), [
                PlayerWarning(player_id=player_id, code="PLAYER_MISSING", message=f"Player {player_id} not found")
            ]

        warnings: List[PlayerWarning] = []
        groups: List[MutationGroup] = []

        if player.breaking_block is not None:
            groups.append(build_abandon_dig_group(player_id=player_id))

        dx, dy, dz = player.direction.value
        target_position = (player.x + dx, player.y + dy, player.z)
        if not player.can_move_to(*target_position):
            warnings.append(
                PlayerWarning(
                    player_id=player_id,
                    code="MOVE_BLOCKED",
                    message=f"Player {player_id} cannot move to {target_position}",
                    details={"target_position": target_position},
                )
            )
            return MutationGroupSequence(groups=groups), warnings

        groups.append(build_move_group(player_id=player_id, target_position=target_position))
        return MutationGroupSequence(groups=groups), warnings


@dataclass
class TurnIntent(PlayerIntent):
    direction: Any

    def build_mutation_group_sequence(self, world: Any, player_id: str) -> Tuple[MutationGroupSequence, List[PlayerWarning]]:
        player = world.get_player(player_id)
        if player is None:
            return MutationGroupSequence(groups=[]), [
                PlayerWarning(player_id=player_id, code="PLAYER_MISSING", message=f"Player {player_id} not found")
            ]

        warnings: List[PlayerWarning] = []
        groups: List[MutationGroup] = []

        if player.breaking_block is not None:
            groups.append(build_abandon_dig_group(player_id=player_id))

        try:
            _coerce_direction(self.direction)
        except ValueError:
            warnings.append(
                PlayerWarning(
                    player_id=player_id,
                    code="INVALID_DIRECTION",
                    message=f"Invalid turn direction: {self.direction}",
                    details={"direction": self.direction},
                )
            )
            return MutationGroupSequence(groups=groups), warnings

        groups.append(build_turn_group(player_id=player_id, direction=self.direction))
        return MutationGroupSequence(groups=groups), warnings


@dataclass
class DigIntent(PlayerIntent):
    target_position: Optional[Tuple[int, int, int]] = None

    def build_mutation_group_sequence(self, world: Any, player_id: str) -> Tuple[MutationGroupSequence, List[PlayerWarning]]:
        player = world.get_player(player_id)
        if player is None:
            return MutationGroupSequence(groups=[]), [
                PlayerWarning(player_id=player_id, code="PLAYER_MISSING", message=f"Player {player_id} not found")
            ]

        warnings: List[PlayerWarning] = []
        target_position = self.target_position or player.breaking_block
        if target_position is None:
            warnings.append(
                PlayerWarning(
                    player_id=player_id,
                    code="NO_DIG_TARGET",
                    message=f"Player {player_id} has no dig target",
                )
            )
            return MutationGroupSequence(groups=[]), warnings

        if not player.is_position_valid(*target_position):
            warnings.append(
                PlayerWarning(
                    player_id=player_id,
                    code="INVALID_DIG_TARGET",
                    message=f"Target {target_position} is out of bounds",
                    details={"target_position": target_position},
                )
            )
            return MutationGroupSequence(groups=[]), warnings

        if not player.can_reach_position(target_position):
            warnings.append(
                PlayerWarning(
                    player_id=player_id,
                    code="DIG_TARGET_OUT_OF_REACH",
                    message=f"Target {target_position} is not reachable",
                    details={"target_position": target_position},
                )
            )
            return MutationGroupSequence(groups=[]), warnings

        block = world.game_state.get_block(*target_position)
        if block is None:
            warnings.append(
                PlayerWarning(
                    player_id=player_id,
                    code="DIG_TARGET_MISSING",
                    message=f"No block exists at {target_position}",
                    details={"target_position": target_position},
                )
            )
            return MutationGroupSequence(groups=[]), warnings

        groups: List[MutationGroup] = []
        if player.breaking_block == target_position and player.break_target_time > 0.0:
            if player.break_progress + 1.0 >= player.break_target_time:
                groups.append(
                    build_dig_finish_group(
                        player_id=player_id,
                        target_position=target_position,
                        block_type=block.block_type,
                    )
                )
            else:
                groups.append(
                    build_dig_continue_group(player_id=player_id, target_position=target_position)
                )
        else:
            break_time = player._get_break_time(block.block_type)
            if (
                player.main_hand_item
                and player.main_hand_item.item_type == ItemType.WOODEN_AXE
                and block.block_type == BlockType.PLANK
            ):
                break_time /= 2.0
            groups.append(
                build_dig_progress_group(
                    player_id=player_id,
                    target_position=target_position,
                    break_time=break_time,
                )
            )

        return MutationGroupSequence(groups=groups), warnings


@dataclass
class PlaceIntent(PlayerIntent):
    block_type_name: str

    def build_mutation_group_sequence(self, world: Any, player_id: str) -> Tuple[MutationGroupSequence, List[PlayerWarning]]:
        player = world.get_player(player_id)
        if player is None:
            return MutationGroupSequence(groups=[]), [
                PlayerWarning(player_id=player_id, code="PLAYER_MISSING", message=f"Player {player_id} not found")
            ]

        warnings: List[PlayerWarning] = []
        groups: List[MutationGroup] = []

        if player.breaking_block is not None:
            groups.append(build_abandon_dig_group(player_id=player_id))

        position = player.resolve_place_position(self.block_type_name)
        if position is None:
            warnings.append(
                PlayerWarning(
                    player_id=player_id,
                    code="INVALID_PLACE_TARGET",
                    message=f"Cannot place {self.block_type_name}",
                    details={"block_type": self.block_type_name},
                )
            )
            return MutationGroupSequence(groups=groups), warnings

        try:
            if self.block_type_name.upper() == "SAPLING":
                block_type = BlockType.SAPLING
            elif self.block_type_name.upper() == "PLANK":
                block_type = BlockType.PLANK
            else:
                raise ValueError(self.block_type_name)
        except ValueError:
            warnings.append(
                PlayerWarning(
                    player_id=player_id,
                    code="INVALID_PLACE_BLOCK_TYPE",
                    message=f"Unsupported block type: {self.block_type_name}",
                    details={"block_type": self.block_type_name},
                )
            )
            return MutationGroupSequence(groups=groups), warnings

        groups.append(build_place_group(player_id=player_id, block_type=block_type, position=position))
        return MutationGroupSequence(groups=groups), warnings


@dataclass
class SwapInventoryIntent(PlayerIntent):
    slot1: int
    slot2: int

    def build_mutation_group_sequence(self, world: Any, player_id: str) -> Tuple[MutationGroupSequence, List[PlayerWarning]]:
        player = world.get_player(player_id)
        if player is None:
            return MutationGroupSequence(groups=[]), [
                PlayerWarning(player_id=player_id, code="PLAYER_MISSING", message=f"Player {player_id} not found")
            ]

        warnings: List[PlayerWarning] = []
        groups: List[MutationGroup] = []

        if player.breaking_block is not None:
            groups.append(build_abandon_dig_group(player_id=player_id))

        if not (
            0 <= self.slot1 < player.maximum_inventory_slots
            and 0 <= self.slot2 < player.maximum_inventory_slots
        ):
            warnings.append(
                PlayerWarning(
                    player_id=player_id,
                    code="INVALID_INVENTORY_SLOT",
                    message=f"Invalid inventory slot(s): {self.slot1}, {self.slot2}",
                    details={"slot1": self.slot1, "slot2": self.slot2},
                )
            )
            return MutationGroupSequence(groups=groups), warnings

        groups.append(build_swap_inventory_group(player_id=player_id, slot1=self.slot1, slot2=self.slot2))
        return MutationGroupSequence(groups=groups), warnings


@dataclass
class CraftAxeIntent(PlayerIntent):
    def build_mutation_group_sequence(self, world: Any, player_id: str) -> Tuple[MutationGroupSequence, List[PlayerWarning]]:
        player = world.get_player(player_id)
        if player is None:
            return MutationGroupSequence(groups=[]), [
                PlayerWarning(player_id=player_id, code="PLAYER_MISSING", message=f"Player {player_id} not found")
            ]

        warnings: List[PlayerWarning] = []
        groups: List[MutationGroup] = []

        if player.breaking_block is not None:
            groups.append(build_abandon_dig_group(player_id=player_id))

        plank_count = 0
        for slot in player.inventory:
            if slot.item and slot.item.item_type == ItemType.PLANK:
                plank_count += slot.item.count
        if plank_count < 3:
            warnings.append(
                PlayerWarning(
                    player_id=player_id,
                    code="NOT_ENOUGH_PLANKS",
                    message="Need at least 3 planks to craft a wooden axe",
                    details={"planks": plank_count},
                )
            )
            return MutationGroupSequence(groups=groups), warnings

        if not player.can_add_item_to_inventory(ItemType.WOODEN_AXE, 1):
            warnings.append(
                PlayerWarning(
                    player_id=player_id,
                    code="INVENTORY_FULL",
                    message="No room to craft a wooden axe",
                )
            )
            return MutationGroupSequence(groups=groups), warnings

        groups.append(build_craft_axe_group(player_id=player_id))
        return MutationGroupSequence(groups=groups), warnings


__all__ = [
    "PlayerIntent",
    "NoIntent",
    "WalkIntent",
    "TurnIntent",
    "DigIntent",
    "PlaceIntent",
    "SwapInventoryIntent",
    "CraftAxeIntent",
]
