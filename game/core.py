from enum import Enum
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

class Direction(Enum):
    EAST = (1, 0, 0)
    SOUTH = (0, 1, 0)
    WEST = (-1, 0, 0)
    NORTH = (0, -1, 0)
    
    @classmethod
    def from_name(cls, name: str) -> 'Direction':
        name = name.upper()
        if name == 'EAST':
            return cls.EAST
        elif name == 'SOUTH':
            return cls.SOUTH
        elif name == 'WEST':
            return cls.WEST
        elif name == 'NORTH':
            return cls.NORTH
        else:
            raise ValueError(f"Invalid direction: {name}")
    
    def opposite(self) -> 'Direction':
        if self == Direction.EAST:
            return Direction.WEST
        elif self == Direction.WEST:
            return Direction.EAST
        elif self == Direction.SOUTH:
            return Direction.NORTH
        elif self == Direction.NORTH:
            return Direction.SOUTH
        raise ValueError("Invalid direction")

class ItemType(Enum):
    SAPLING = "sapling"
    PLANK = "plank"
    WOODEN_AXE = "wooden_axe"

class BlockType(Enum):
    SAPLING = "sapling"
    PLANK = "plank"
    LEAF = "leaf"

    def to_item_type(self) -> "ItemType":
        if self == BlockType.SAPLING:
            return ItemType.SAPLING
        if self == BlockType.PLANK:
            return ItemType.PLANK
        if self == BlockType.LEAF:
            return ItemType.SAPLING
        return ItemType.SAPLING

@dataclass
class Block:
    block_type: BlockType
    x: int
    y: int
    z: int
    has_entity: bool = False
    break_progress: float = 0.0  # 0.0 to 1.0
    
    def __post_init__(self):
        if self.block_type == BlockType.SAPLING:
            self.has_entity = False
        elif self.block_type == BlockType.PLANK:
            self.has_entity = True
        elif self.block_type == BlockType.LEAF:
            self.has_entity = True

@dataclass
class Item:
    item_type: ItemType
    count: int = 1
    
    def can_stack_with(self, other: 'Item') -> bool:
        return self.item_type == other.item_type
    
    def max_stack(self) -> int:
        if self.item_type == ItemType.SAPLING:
            return 8
        elif self.item_type == ItemType.PLANK:
            return 8
        elif self.item_type == ItemType.WOODEN_AXE:
            return 1
        return 1

@dataclass
class InventorySlot:
    item: Optional[Item] = None
    
    def is_empty(self) -> bool:
        return self.item is None or self.item.count == 0
    
    def can_accept(self, new_item: Item) -> bool:
        if self.is_empty():
            return new_item.count <= new_item.max_stack()
        if self.item.item_type != new_item.item_type:
            return False
        return self.item.count + new_item.count <= self.item.max_stack()

class GameState:
    def __init__(self):
        self.world_size = 5
        self.world_center = (
            self.world_size // 2,
            self.world_size // 2,
            self.world_size // 2,
        )
        self.blocks: Dict[Tuple[int, int, int], Block] = {}
        self.tick_count = 0
        
    def add_block(self, block: Block) -> bool:
        pos = (block.x, block.y, block.z)
        if pos in self.blocks:
            return False
        # Check bounds
        x, y, z = pos
        if not (0 <= x < self.world_size and 0 <= y < self.world_size and 0 <= z < self.world_size):
            return False
        self.blocks[pos] = block
        return True
    
    def remove_block(self, x: int, y: int, z: int) -> Optional[Block]:
        pos = (x, y, z)
        return self.blocks.pop(pos, None)
    
    def get_block(self, x: int, y: int, z: int) -> Optional[Block]:
        return self.blocks.get((x, y, z))
    
    def is_adjacent_to_block(self, x: int, y: int, z: int) -> bool:
        """Check if position is adjacent to any existing block or on ground level (z=0)"""
        if z == 0:
            return True
        neighbors = [(x+1,y,z), (x-1,y,z), (x,y+1,z), (x,y-1,z), (x,y,z+1), (x,y,z-1)]
        for nx, ny, nz in neighbors:
            if (nx, ny, nz) in self.blocks:
                return True
        return False


from .mutations import (  # noqa: E402  # re-exported compatibility layer
    Mutation,
    MutationGroup,
    MutationGroupSequence,
    MutationSequence,
    NoOpMutation,
    PlayerWarning,
)


__all__ = [
    "Direction",
    "ItemType",
    "BlockType",
    "Block",
    "Item",
    "InventorySlot",
    "GameState",
    "Mutation",
    "NoOpMutation",
    "MutationGroup",
    "MutationSequence",
    "MutationGroupSequence",
    "PlayerWarning",
]
