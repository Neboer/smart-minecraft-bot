from enum import Enum
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import random

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
        self.world_center = (0, 0, 2)
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
    
    def process_tick(self):
        """Process one tick of world simulation"""
        self.tick_count += 1
        self._process_tree_growth()
    
    def _process_tree_growth(self):
        """Process sapling growth into trees"""
        saplings = [(pos, block) for pos, block in self.blocks.items() 
                   if block.block_type == BlockType.SAPLING]
        
        for pos, sapling in saplings:
            x, y, z = pos
            # Check if sapling is at ground level (height 0)
            if z != 0:
                continue
            
            # Check if there are no other blocks within 4 blocks (Manhattan distance)
            has_neighbor = False
            for other_pos, other_block in self.blocks.items():
                if other_pos == pos:
                    continue
                ox, oy, oz = other_pos
                if abs(ox - x) + abs(oy - y) + abs(oz - z) <= 4:
                    has_neighbor = True
                    break
            
            if has_neighbor:
                continue
            
            # 10% chance to grow into tree
            if random.random() < 0.1:
                # Remove sapling
                self.remove_block(x, y, z)
                # Create tree: 2-4 planks vertically + 1 leaf on top
                trunk_height = random.randint(2, 4)
                for h in range(trunk_height):
                    plank = Block(BlockType.PLANK, x, y, z + h)
                    self.add_block(plank)
                leaf = Block(BlockType.LEAF, x, y, z + trunk_height)
                self.add_block(leaf)
