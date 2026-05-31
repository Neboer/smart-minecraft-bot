from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Vec3I(tuple[int, int, int]):
    def __new__(cls, x: int, y: int, z: int) -> "Vec3I":
        return super().__new__(cls, (x, y, z))

    @property
    def x(self) -> int:
        return self[0]

    @property
    def y(self) -> int:
        return self[1]

    @property
    def z(self) -> int:
        return self[2]

    def __add__(self, other: tuple[int, int, int]) -> "Vec3I":  # type: ignore[override]
        return Vec3I(self[0] + other[0], self[1] + other[1], self[2] + other[2])

    def __sub__(self, other: tuple[int, int, int]) -> "Vec3I":
        return Vec3I(self[0] - other[0], self[1] - other[1], self[2] - other[2])

    def __repr__(self) -> str:
        return f"Vec3I({self[0]}, {self[1]}, {self[2]})"


class Direction(Enum):
    EAST = (1, 0, 0)
    SOUTH = (0, 1, 0)
    WEST = (-1, 0, 0)
    NORTH = (0, -1, 0)

    @classmethod
    def from_name(cls, name: str) -> "Direction":
        name = name.upper()
        for member in cls:
            if member.name == name:
                return member
        raise ValueError(f"Invalid direction: {name}")

    def opposite(self) -> "Direction":
        mapping = {
            Direction.EAST: Direction.WEST,
            Direction.WEST: Direction.EAST,
            Direction.SOUTH: Direction.NORTH,
            Direction.NORTH: Direction.SOUTH,
        }
        return mapping[self]

    def as_vec3i(self) -> Vec3I:
        dx, dy, dz = self.value
        return Vec3I(dx, dy, dz)


class ItemType(Enum):
    SAPLING = "sapling"
    PLANK = "plank"
    WOODEN_AXE = "wooden_axe"


class BlockType(Enum):
    SAPLING = "sapling"
    PLANK = "plank"
    LEAF = "leaf"

    def to_item_type(self) -> "ItemType":
        mapping: dict[BlockType, ItemType] = {
            BlockType.SAPLING: ItemType.SAPLING,
            BlockType.PLANK: ItemType.PLANK,
            BlockType.LEAF: ItemType.SAPLING,
        }
        return mapping[self]

    def has_entity(self) -> bool:
        return self in (BlockType.PLANK, BlockType.LEAF)


@dataclass
class Block:
    block_type: BlockType
    x: int
    y: int
    z: int
    has_entity: bool = False
    break_progress: float = 0.0

    def __post_init__(self) -> None:
        self.has_entity = self.block_type.has_entity()

    @property
    def position(self) -> Vec3I:
        return Vec3I(self.x, self.y, self.z)


@dataclass
class Item:
    item_type: ItemType
    count: int = 1

    def max_stack(self) -> int:
        from .data import ITEM_MAX_STACK
        return ITEM_MAX_STACK[self.item_type]

    def can_stack_with(self, other: "Item") -> bool:
        return self.item_type == other.item_type

    def to_block_type(self) -> BlockType | None:
        try:
            return BlockType(self.item_type.value)
        except ValueError:
            return None


@dataclass
class InventorySlot:
    item: Item | None = None

    def is_empty(self) -> bool:
        return self.item is None or self.item.count == 0

    def can_accept(self, new_item: Item) -> bool:
        if self.is_empty():
            return new_item.count <= new_item.max_stack()
        if self.item.item_type != new_item.item_type:
            return False
        return self.item.count + new_item.count <= self.item.max_stack()


class GameState:
    def __init__(self) -> None:
        self.world_size: int = 5
        self.blocks: dict[tuple[int, int, int], Block] = {}
        self.tick_count: int = 0

    def add_block(self, block: Block) -> bool:
        pos = (block.x, block.y, block.z)
        if pos in self.blocks:
            return False
        x, y, z = pos
        if not (0 <= x < self.world_size and 0 <= y < self.world_size and 0 <= z < self.world_size):
            return False
        self.blocks[pos] = block
        return True

    def remove_block(self, x: int, y: int, z: int) -> Block | None:
        return self.blocks.pop((x, y, z), None)

    def get_block(self, x: int, y: int, z: int) -> Block | None:
        return self.blocks.get((x, y, z))

    def is_adjacent_to_block(self, x: int, y: int, z: int) -> bool:
        if z == 0:
            return True
        for nx, ny, nz in [(x+1,y,z),(x-1,y,z),(x,y+1,z),(x,y-1,z),(x,y,z+1),(x,y,z-1)]:
            if (nx, ny, nz) in self.blocks:
                return True
        return False


def _serialize_value(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_serialize_value(v) for v in value]
    return value


@dataclass
class PlayerWarning:
    player_id: str
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "player_id": self.player_id,
            "code": self.code,
            "message": self.message,
            "details": _serialize_value(self.details),
        }


__all__ = [
    "Vec3I",
    "Direction",
    "ItemType",
    "BlockType",
    "Block",
    "Item",
    "InventorySlot",
    "GameState",
    "PlayerWarning",
]
