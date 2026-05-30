from __future__ import annotations

from dataclasses import dataclass, field, is_dataclass
from enum import Enum
from itertools import product
import random
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

from .core import Block, BlockType, Direction, GameState, Item, ItemType


def _serialize_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _serialize_value(inner) for key, inner in value.__dict__.items()}
    if isinstance(value, dict):
        return {key: _serialize_value(inner) for key, inner in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_serialize_value(inner) for inner in value]
    return value


@dataclass
class PlayerWarning:
    player_id: str
    code: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "player_id": self.player_id,
            "code": self.code,
            "message": self.message,
            "details": _serialize_value(self.details),
        }


class Mutation:
    """Base mutation object.

    Mutations are the smallest world-changing units. They carry conditions,
    parameters, and execution logic, and are only applied when their
    preconditions still hold.
    """

    def __init__(
        self,
        parameters: Optional[Dict[str, Any]] = None,
        *,
        probability: float = 1.0,
        description: Optional[str] = None,
        apply: Optional[Callable[[], Dict[str, Any]]] = None,
        conditions: Optional[Callable[[Any], bool]] = None,
    ):
        self.parameters = parameters or {}
        self.probability = probability
        self.description = description or self.__class__.__name__
        self._apply_callback = apply
        self._conditions_callback = conditions

    def check_conditions(self, world_state: Any) -> bool:
        if self._conditions_callback is not None:
            return bool(self._conditions_callback(world_state))
        return True

    def _execute(self, world_state: Any) -> Dict[str, Any]:
        return {"success": True}

    def execute(self, world_state: Any) -> Dict[str, Any]:
        if not self.check_conditions(world_state):
            return {
                "success": False,
                "noop": True,
                "reason": "conditions_failed",
                "mutation": self.description,
            }

        if self._apply_callback is not None:
            result = self._apply_callback()
            if isinstance(result, dict):
                result = dict(result)
                result.setdefault("success", True)
                return result
            return {"success": True, "result": result}

        result = self._execute(world_state)
        if isinstance(result, dict):
            result = dict(result)
            result.setdefault("success", True)
            return result
        return {"success": True, "result": result}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mutation_type": self.__class__.__name__,
            "description": self.description,
            "probability": self.probability,
            "parameters": _serialize_value(self.parameters),
        }


class NoOpMutation(Mutation):
    def __init__(self, parameters: Optional[Dict[str, Any]] = None, *, probability: float = 1.0, description: Optional[str] = None):
        super().__init__(parameters=parameters, probability=probability, description=description or "NOOP")

    def _execute(self, world_state: Any) -> Dict[str, Any]:
        return {"success": True, "noop": True}


@dataclass
class MutationGroup:
    mutations: List[Mutation]
    name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "mutations": [mutation.to_dict() for mutation in self.mutations],
        }


@dataclass
class MutationSequence:
    mutations: List[Mutation]
    probability: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "probability": self.probability,
            "mutations": [mutation.to_dict() for mutation in self.mutations],
        }


@dataclass
class MutationGroupSequence:
    groups: List[MutationGroup]

    def merge(self, other: "MutationGroupSequence") -> "MutationGroupSequence":
        return MutationGroupSequence(groups=[*self.groups, *other.groups])

    def __add__(self, other: "MutationGroupSequence") -> "MutationGroupSequence":
        return self.merge(other)

    def __iter__(self) -> Iterator[MutationSequence]:
        return self.iter_sequences()

    def iter_sequences(self) -> Iterator[MutationSequence]:
        active_groups: List[List[Mutation]] = [group.mutations for group in self.groups if group.mutations]
        if not active_groups:
            yield MutationSequence(mutations=[], probability=1.0)
            return

        for combination in product(*active_groups):
            probability = 1.0
            for mutation in combination:
                probability *= mutation.probability
            yield MutationSequence(mutations=list(combination), probability=probability)

    def sample_sequence(self, rng: Optional[random.Random] = None) -> MutationSequence:
        rng_obj: Any = rng if rng is not None else random
        selected: List[Mutation] = []
        probability = 1.0

        for group in self.groups:
            if not group.mutations:
                continue

            weights = [max(0.0, mutation.probability) for mutation in group.mutations]
            if sum(weights) <= 0:
                chosen = rng_obj.choice(group.mutations)
            else:
                chosen = rng_obj.choices(group.mutations, weights=weights, k=1)[0]
            selected.append(chosen)
            probability *= chosen.probability

        return MutationSequence(mutations=selected, probability=probability)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "groups": [group.to_dict() for group in self.groups],
        }


def _get_player(world_state: Any, player_id: str):
    return world_state.get_player(player_id)


def _coerce_direction(direction: Any) -> Direction:
    if isinstance(direction, Direction):
        return direction
    return Direction.from_name(str(direction))


def _resolve_placement_position(player: Any, block_type: BlockType) -> Optional[Tuple[int, int, int]]:
    facing_low = player.get_facing_block_position()
    facing_high = player.get_facing_block_position_high()
    below = player.get_position_below()

    possible_positions = [facing_low, facing_high, below]
    for position in possible_positions:
        x, y, z = position
        if not player.is_position_valid(x, y, z):
            continue
        if player.game_state.get_block(x, y, z) is not None:
            continue

        if position == below:
            if block_type == BlockType.SAPLING:
                if z != 0:
                    continue
            else:
                above_player = (player.x, player.y, player.z + player.height)
                if player.game_state.get_block(*above_player) is not None:
                    continue

        if not player.game_state.is_adjacent_to_block(x, y, z):
            continue

        return position

    return None


def _block_drop_options(block_type: BlockType) -> List[Tuple[int, float, ItemType]]:
    if block_type == BlockType.SAPLING:
        return [(1, 1.0, ItemType.SAPLING)]
    if block_type == BlockType.PLANK:
        return [(1, 1.0, ItemType.PLANK)]
    if block_type == BlockType.LEAF:
        return [
            (1, 1.0 / 3.0, ItemType.SAPLING),
            (2, 1.0 / 3.0, ItemType.SAPLING),
            (3, 1.0 / 3.0, ItemType.SAPLING),
        ]
    return []


def _tree_growth_conditions(world_state: Any, position: Tuple[int, int, int], trunk_height: int) -> bool:
    x, y, z = position
    if z != 0:
        return False

    sapling = world_state.game_state.get_block(x, y, z)
    if sapling is None or sapling.block_type != BlockType.SAPLING:
        return False

    neighbor_xy = {(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)}
    for other_pos, other_block in world_state.game_state.blocks.items():
        if other_pos == position:
            continue
        ox, oy, oz = other_pos
        if (ox, oy) == (x, y):
            return False
        if (ox, oy) in neighbor_xy:
            return False

    for height in range(trunk_height):
        if world_state.game_state.get_block(x, y, z + height) not in (None, sapling):
            return False
    if world_state.game_state.get_block(x, y, z + trunk_height) is not None:
        return False
    return True


class MovePlayerMutation(Mutation):
    def __init__(self, *, player_id: str, target_position: Tuple[int, int, int], probability: float = 1.0):
        super().__init__(
            parameters={"player_id": player_id, "target_position": target_position},
            probability=probability,
            description=f"Move player {player_id} to {target_position}",
        )

    def check_conditions(self, world_state: Any) -> bool:
        player = _get_player(world_state, self.parameters["player_id"])
        if player is None:
            return False
        x, y, z = self.parameters["target_position"]
        return player.can_move_to(x, y, z)

    def _execute(self, world_state: Any) -> Dict[str, Any]:
        player = _get_player(world_state, self.parameters["player_id"])
        if player is None:
            return {"success": False, "error": "Player not found"}
        x, y, z = self.parameters["target_position"]
        player.x, player.y, player.z = x, y, z
        return {"success": True, "position": (x, y, z)}


class TurnPlayerMutation(Mutation):
    def __init__(self, *, player_id: str, direction: Any, probability: float = 1.0):
        coerced = _coerce_direction(direction)
        super().__init__(
            parameters={"player_id": player_id, "direction": coerced},
            probability=probability,
            description=f"Turn player {player_id} to {coerced.name.lower()}",
        )

    def check_conditions(self, world_state: Any) -> bool:
        player = _get_player(world_state, self.parameters["player_id"])
        return player is not None

    def _execute(self, world_state: Any) -> Dict[str, Any]:
        player = _get_player(world_state, self.parameters["player_id"])
        if player is None:
            return {"success": False, "error": "Player not found"}
        direction = self.parameters["direction"]
        player.direction = direction
        return {"success": True, "direction": direction.name.lower()}


class AbandonDigMutation(Mutation):
    def __init__(self, *, player_id: str, probability: float = 1.0):
        super().__init__(
            parameters={"player_id": player_id},
            probability=probability,
            description=f"Abandon digging for {player_id}",
        )

    def check_conditions(self, world_state: Any) -> bool:
        player = _get_player(world_state, self.parameters["player_id"])
        return player is not None and player.breaking_block is not None

    def _execute(self, world_state: Any) -> Dict[str, Any]:
        player = _get_player(world_state, self.parameters["player_id"])
        if player is None:
            return {"success": False, "error": "Player not found"}
        abandoned = player.breaking_block
        player.breaking_block = None
        player.break_progress = 0.0
        player.break_target_time = 0.0
        return {"success": True, "abandoned": abandoned}


class BeginDigMutation(Mutation):
    def __init__(self, *, player_id: str, target_position: Tuple[int, int, int], break_time: float, probability: float = 1.0):
        super().__init__(
            parameters={
                "player_id": player_id,
                "target_position": target_position,
                "break_time": break_time,
            },
            probability=probability,
            description=f"Begin digging {target_position} for {player_id}",
        )

    def check_conditions(self, world_state: Any) -> bool:
        player = _get_player(world_state, self.parameters["player_id"])
        if player is None:
            return False
        target = self.parameters["target_position"]
        if not player.is_position_valid(*target):
            return False
        block = player.game_state.get_block(*target)
        if block is None:
            return False
        return target in [
            player.get_facing_block_position(),
            player.get_facing_block_position_high(),
            player.get_position_below(),
        ]

    def _execute(self, world_state: Any) -> Dict[str, Any]:
        player = _get_player(world_state, self.parameters["player_id"])
        if player is None:
            return {"success": False, "error": "Player not found"}
        target = self.parameters["target_position"]
        player.breaking_block = target
        player.break_progress = 0.0
        player.break_target_time = float(self.parameters["break_time"])
        return {
            "success": True,
            "breaking_block": target,
            "break_time": player.break_target_time,
        }


class ContinueDigMutation(Mutation):
    def __init__(self, *, player_id: str, target_position: Tuple[int, int, int], probability: float = 1.0):
        super().__init__(
            parameters={"player_id": player_id, "target_position": target_position},
            probability=probability,
            description=f"Continue digging {target_position} for {player_id}",
        )

    def check_conditions(self, world_state: Any) -> bool:
        player = _get_player(world_state, self.parameters["player_id"])
        if player is None:
            return False
        target = self.parameters["target_position"]
        block = player.game_state.get_block(*target)
        return (
            player.breaking_block == target
            and block is not None
            and player.break_progress + 1.0 < player.break_target_time
        )

    def _execute(self, world_state: Any) -> Dict[str, Any]:
        player = _get_player(world_state, self.parameters["player_id"])
        if player is None:
            return {"success": False, "error": "Player not found"}
        player.break_progress += 1.0
        return {"success": True, "break_progress": player.break_progress}


class FinishDigMutation(Mutation):
    def __init__(
        self,
        *,
        player_id: str,
        target_position: Tuple[int, int, int],
        drop_count: int,
        drop_probability: float,
        drop_item_type: ItemType,
    ):
        super().__init__(
            parameters={
                "player_id": player_id,
                "target_position": target_position,
                "drop_count": drop_count,
                "drop_probability": drop_probability,
                "drop_item_type": drop_item_type,
            },
            probability=drop_probability,
            description=f"Finish digging {target_position} for {player_id} (x{drop_count} {drop_item_type.value})",
        )

    def check_conditions(self, world_state: Any) -> bool:
        player = _get_player(world_state, self.parameters["player_id"])
        if player is None:
            return False
        target = self.parameters["target_position"]
        block = player.game_state.get_block(*target)
        if block is None:
            return False
        if player.breaking_block != target:
            return False
        if player.break_progress + 1.0 < player.break_target_time:
            return False
        drop_count = int(self.parameters["drop_count"])
        drop_item_type = self.parameters["drop_item_type"]
        return player.can_add_item_to_inventory(drop_item_type, drop_count)

    def _execute(self, world_state: Any) -> Dict[str, Any]:
        player = _get_player(world_state, self.parameters["player_id"])
        if player is None:
            return {"success": False, "error": "Player not found"}

        target = self.parameters["target_position"]
        block = player.game_state.remove_block(*target)
        if block is None:
            return {"success": False, "error": "Target block vanished"}

        drop_item_type = self.parameters["drop_item_type"]
        drop_count = int(self.parameters["drop_count"])
        if not player._add_item_to_inventory(drop_item_type, drop_count):
            return {"success": False, "error": "Inventory full, cannot collect drops"}

        player.breaking_block = None
        player.break_progress = 0.0
        player.break_target_time = 0.0
        return {
            "success": True,
            "removed_block": block.block_type.value,
            "dropped_item": drop_item_type.value,
            "count": drop_count,
        }


class PlaceBlockMutation(Mutation):
    def __init__(
        self,
        *,
        player_id: str,
        block_type: BlockType,
        position: Tuple[int, int, int],
        probability: float = 1.0,
    ):
        super().__init__(
            parameters={
                "player_id": player_id,
                "block_type": block_type,
                "position": position,
            },
            probability=probability,
            description=f"Place {block_type.value} at {position} for {player_id}",
        )

    def check_conditions(self, world_state: Any) -> bool:
        player = _get_player(world_state, self.parameters["player_id"])
        if player is None:
            return False
        position = self.parameters["position"]
        block_type = self.parameters["block_type"]
        resolved = _resolve_placement_position(player, block_type)
        if resolved != position:
            return False
        main_hand = player.main_hand_item
        if main_hand is None:
            return False
        return main_hand.item_type == block_type.to_item_type()

    def _execute(self, world_state: Any) -> Dict[str, Any]:
        player = _get_player(world_state, self.parameters["player_id"])
        if player is None:
            return {"success": False, "error": "Player not found"}

        position = self.parameters["position"]
        block_type = self.parameters["block_type"]
        x, y, z = position
        new_block = Block(block_type, x, y, z)
        if not player.game_state.add_block(new_block):
            return {"success": False, "error": "Failed to place block"}

        main_hand_item = player.inventory[player.main_hand_slot].item
        if main_hand_item is None:
            return {"success": False, "error": "Main hand item missing"}
        main_hand_item.count -= 1
        if main_hand_item.count <= 0:
            player.inventory[player.main_hand_slot].item = None

        return {
            "success": True,
            "position": position,
            "block_type": block_type.value,
        }


class SwapInventoryMutation(Mutation):
    def __init__(self, *, player_id: str, slot1: int, slot2: int, probability: float = 1.0):
        super().__init__(
            parameters={"player_id": player_id, "slot1": slot1, "slot2": slot2},
            probability=probability,
            description=f"Swap inventory slots {slot1} and {slot2} for {player_id}",
        )

    def check_conditions(self, world_state: Any) -> bool:
        player = _get_player(world_state, self.parameters["player_id"])
        if player is None:
            return False
        slot1 = int(self.parameters["slot1"])
        slot2 = int(self.parameters["slot2"])
        return 0 <= slot1 < player.maximum_inventory_slots and 0 <= slot2 < player.maximum_inventory_slots

    def _execute(self, world_state: Any) -> Dict[str, Any]:
        player = _get_player(world_state, self.parameters["player_id"])
        if player is None:
            return {"success": False, "error": "Player not found"}
        slot1 = int(self.parameters["slot1"])
        slot2 = int(self.parameters["slot2"])
        player.inventory[slot1].item, player.inventory[slot2].item = (
            player.inventory[slot2].item,
            player.inventory[slot1].item,
        )
        return {"success": True, "slots": (slot1, slot2)}


class CraftAxeMutation(Mutation):
    def __init__(self, *, player_id: str, probability: float = 1.0):
        super().__init__(
            parameters={"player_id": player_id},
            probability=probability,
            description=f"Craft wooden axe for {player_id}",
        )

    def check_conditions(self, world_state: Any) -> bool:
        player = _get_player(world_state, self.parameters["player_id"])
        if player is None:
            return False

        plank_count = 0
        for slot in player.inventory:
            if slot.item and slot.item.item_type == ItemType.PLANK:
                plank_count += slot.item.count
        if plank_count < 3:
            return False
        return player.can_add_item_to_inventory(ItemType.WOODEN_AXE, 1)

    def _execute(self, world_state: Any) -> Dict[str, Any]:
        player = _get_player(world_state, self.parameters["player_id"])
        if player is None:
            return {"success": False, "error": "Player not found"}

        remaining = 3
        for slot in player.inventory:
            if remaining <= 0:
                break
            if slot.item and slot.item.item_type == ItemType.PLANK:
                to_remove = min(remaining, slot.item.count)
                slot.item.count -= to_remove
                remaining -= to_remove
                if slot.item.count <= 0:
                    slot.item = None

        if not player._add_item_to_inventory(ItemType.WOODEN_AXE, 1):
            return {"success": False, "error": "No room for wooden axe"}

        return {"success": True, "crafted": ItemType.WOODEN_AXE.value}


class SaplingIdleGrowthMutation(Mutation):
    def __init__(self, *, position: Tuple[int, int, int], probability: float = 1.0):
        super().__init__(
            parameters={"position": position},
            probability=probability,
            description=f"Sapling at {position} does not grow",
        )

    def check_conditions(self, world_state: Any) -> bool:
        x, y, z = self.parameters["position"]
        block = world_state.game_state.get_block(x, y, z)
        return block is not None and block.block_type == BlockType.SAPLING

    def _execute(self, world_state: Any) -> Dict[str, Any]:
        return {"success": True, "grown": False, "position": self.parameters["position"]}


class SaplingGrowthMutation(Mutation):
    def __init__(self, *, position: Tuple[int, int, int], trunk_height: int, probability: float = 1.0):
        super().__init__(
            parameters={"position": position, "trunk_height": trunk_height},
            probability=probability,
            description=f"Sapling at {position} grows to {trunk_height}",
        )

    def check_conditions(self, world_state: Any) -> bool:
        position = self.parameters["position"]
        trunk_height = int(self.parameters["trunk_height"])
        return _tree_growth_conditions(world_state, position, trunk_height)

    def _execute(self, world_state: Any) -> Dict[str, Any]:
        position = self.parameters["position"]
        trunk_height = int(self.parameters["trunk_height"])
        x, y, z = position
        sapling = world_state.game_state.remove_block(x, y, z)
        if sapling is None:
            return {"success": False, "error": "Sapling vanished"}

        for height in range(trunk_height):
            plank = Block(BlockType.PLANK, x, y, z + height)
            world_state.game_state.add_block(plank)
        leaf = Block(BlockType.LEAF, x, y, z + trunk_height)
        world_state.game_state.add_block(leaf)
        return {
            "success": True,
            "grown": True,
            "height": trunk_height,
            "position": position,
        }


def build_tree_growth_mutation_group(position: Tuple[int, int, int]) -> MutationGroup:
    mutations: List[Mutation] = [
        SaplingIdleGrowthMutation(position=position, probability=0.9),
    ]
    for trunk_height in (2, 3, 4):
        mutations.append(
            SaplingGrowthMutation(position=position, trunk_height=trunk_height, probability=0.1 / 3.0)
        )
    return MutationGroup(mutations=mutations, name=f"tree_growth:{position}")


def build_dig_finish_group(
    *,
    player_id: str,
    target_position: Tuple[int, int, int],
    block_type: BlockType,
) -> MutationGroup:
    drop_options = _block_drop_options(block_type)
    mutations: List[Mutation] = []
    for drop_count, probability, item_type in drop_options:
        mutations.append(
            FinishDigMutation(
                player_id=player_id,
                target_position=target_position,
                drop_count=drop_count,
                drop_probability=probability,
                drop_item_type=item_type,
            )
        )
    return MutationGroup(mutations=mutations, name=f"dig_finish:{player_id}:{target_position}")


def build_dig_progress_group(*, player_id: str, target_position: Tuple[int, int, int], break_time: float) -> MutationGroup:
    return MutationGroup(
        mutations=[
            BeginDigMutation(player_id=player_id, target_position=target_position, break_time=break_time),
        ],
        name=f"dig_start:{player_id}:{target_position}",
    )


def build_dig_continue_group(*, player_id: str, target_position: Tuple[int, int, int]) -> MutationGroup:
    return MutationGroup(
        mutations=[
            ContinueDigMutation(player_id=player_id, target_position=target_position),
        ],
        name=f"dig_continue:{player_id}:{target_position}",
    )


def build_abandon_dig_group(*, player_id: str) -> MutationGroup:
    return MutationGroup(
        mutations=[
            AbandonDigMutation(player_id=player_id),
        ],
        name=f"dig_abandon:{player_id}",
    )


def build_move_group(*, player_id: str, target_position: Tuple[int, int, int]) -> MutationGroup:
    return MutationGroup(
        mutations=[
            MovePlayerMutation(player_id=player_id, target_position=target_position),
        ],
        name=f"move:{player_id}:{target_position}",
    )


def build_turn_group(*, player_id: str, direction: Any) -> MutationGroup:
    return MutationGroup(
        mutations=[
            TurnPlayerMutation(player_id=player_id, direction=direction),
        ],
        name=f"turn:{player_id}:{str(direction).lower()}",
    )


def build_place_group(*, player_id: str, block_type: BlockType, position: Tuple[int, int, int]) -> MutationGroup:
    return MutationGroup(
        mutations=[
            PlaceBlockMutation(player_id=player_id, block_type=block_type, position=position),
        ],
        name=f"place:{player_id}:{block_type.value}:{position}",
    )


def build_swap_inventory_group(*, player_id: str, slot1: int, slot2: int) -> MutationGroup:
    return MutationGroup(
        mutations=[
            SwapInventoryMutation(player_id=player_id, slot1=slot1, slot2=slot2),
        ],
        name=f"swap:{player_id}:{slot1}:{slot2}",
    )


def build_craft_axe_group(*, player_id: str) -> MutationGroup:
    return MutationGroup(
        mutations=[
            CraftAxeMutation(player_id=player_id),
        ],
        name=f"craft_axe:{player_id}",
    )
