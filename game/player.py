from typing import List, Dict, Tuple, Optional, Any
from .core import Direction, ItemType, BlockType, Item, InventorySlot, Block, GameState


class Player:
    def __init__(
        self,
        game_state: GameState,
        x: int = 0,
        y: int = 0,
        z: int = 0,
        direction: Direction = Direction.EAST,
    ):
        self.game_state = game_state
        self.x = x
        self.y = y
        self.z = z
        self.direction = direction
        self.height = 2  # Player height
        self.maximum_inventory_slots = 10
        self.inventory = [
            InventorySlot() for _ in range(self.maximum_inventory_slots)
        ]  # self.player_maximum_inventory_slots slots (0-9   with 0 as main hand slot   )
        self.breaking_block: Optional[Tuple[int, int, int]] = None
        self.break_progress: float = 0.0
        self.break_target_time: float = 0.0

        # Initialize with one sapling in slot 0
        self.inventory[0].item = Item(ItemType.SAPLING, 1)

    @property
    def main_hand_slot(self) -> int:
        return 0

    @property
    def main_hand_item(self) -> Optional[Item]:
        return self.inventory[self.main_hand_slot].item

    def swap_inventory_slots(self, slot1: int, slot2: int) -> Dict[str, Any]:
        """Swap items between two inventory slots. Does not consume tick."""
        if not (
            0 <= slot1 < self.maximum_inventory_slots
            and 0 <= slot2 < self.maximum_inventory_slots
        ):
            return {"success": False, "error": "Invalid slot index"}

        # Swap the items
        self.inventory[slot1].item, self.inventory[slot2].item = (
            self.inventory[slot2].item,
            self.inventory[slot1].item,
        )
        return {"success": True}

    def get_facing_block_position(self) -> Tuple[int, int, int]:
        """Get the position of the block in front of the player"""
        dx, dy, dz = self.direction.value
        return (self.x + dx, self.y + dy, self.z)

    def get_facing_block_position_high(self) -> Tuple[int, int, int]:
        """Get the position of the block in front of the player at player's height"""
        dx, dy, dz = self.direction.value
        return (self.x + dx, self.y + dy, self.z + 1)

    def get_position_below(self) -> Tuple[int, int, int]:
        """Get the position directly below the player"""
        return (self.x, self.y, self.z - 1)

    def is_position_valid(self, x: int, y: int, z: int) -> bool:
        """Check if a position is within world bounds"""
        world_size = self.game_state.world_size
        return 0 <= x < world_size and 0 <= y < world_size and 0 <= z < world_size

    def can_move_to(self, x: int, y: int, z: int) -> bool:
        """Check if player can move to position (collision detection)"""
        if not self.is_position_valid(x, y, z):
            return False

        # Check for blocks that would block movement (height 2)
        for h in range(self.height):
            block_pos = (x, y, z + h)
            if block_pos in self.game_state.blocks:
                return False

        return True

    def move_forward(self) -> Dict[str, Any]:
        """Move forward one block in current direction. Costs 1 tick."""
        dx, dy, dz = self.direction.value
        new_x, new_y, new_z = self.x + dx, self.y + dy, self.z

        if not self.can_move_to(new_x, new_y, new_z):
            return {"success": False, "error": "Cannot move to target position"}

        self.x, self.y, self.z = new_x, new_y, new_z
        return {"success": True, "consumed_tick": True}

    def turn_to(self, direction_name: str) -> Dict[str, Any]:
        """Turn to face a direction. Costs 1 tick."""
        try:
            new_direction = Direction.from_name(direction_name)
        except ValueError:
            return {"success": False, "error": "Invalid direction"}

        if new_direction == self.direction:
            return {"success": True, "consumed_tick": True}

        self.direction = new_direction
        return {"success": True, "consumed_tick": True}

    def _get_break_time(self, block_type: BlockType) -> float:
        """Get base break time for a block type"""
        if block_type == BlockType.SAPLING:
            return 1.0
        elif block_type == BlockType.PLANK:
            return 4.0
        elif block_type == BlockType.LEAF:
            return 1.0
        return 1.0

    def start_breaking_block(self, x: int, y: int, z: int) -> Dict[str, Any]:
        """Start breaking a block at position. Costs 1 tick."""
        if not self.is_position_valid(x, y, z):
            return {"success": False, "error": "Invalid position"}

        block = self.game_state.get_block(x, y, z)
        if block is None:
            return {"success": False, "error": "No block at position"}

        # Check if player is facing this block (must be at same height or +1, or below)
        facing_low = self.get_facing_block_position()
        facing_high = self.get_facing_block_position_high()
        below = self.get_position_below()

        target_pos = (x, y, z)
        if target_pos not in [facing_low, facing_high, below]:
            return {"success": False, "error": "Block not in reach"}

        # If already breaking a different block, reset progress
        if self.breaking_block and self.breaking_block != target_pos:
            self.breaking_block = None
            self.break_progress = 0.0

        self.breaking_block = target_pos

        # Calculate break time
        break_time = self._get_break_time(block.block_type)

        # Wooden axe doubles speed for planks
        if (
            self.main_hand_item
            and self.main_hand_item.item_type == ItemType.WOODEN_AXE
            and block.block_type == BlockType.PLANK
        ):
            break_time /= 2.0

        self.break_target_time = break_time
        return {"success": True, "consumed_tick": True}

    def continue_breaking_block(self) -> Dict[str, Any]:
        """Continue breaking the current block. Costs 1 tick."""
        if not self.breaking_block:
            return {"success": False, "error": "Not breaking any block"}

        self.break_progress += 1.0

        if self.break_progress >= self.break_target_time:
            # Block is broken
            x, y, z = self.breaking_block
            block = self.game_state.remove_block(x, y, z)

            if block:
                # Generate drops
                drops = self._generate_drops(block)
                self.breaking_block = None
                self.break_progress = 0.0

                # Add drops to inventory
                for drop_type, drop_count in drops:
                    added = self._add_item_to_inventory(drop_type, drop_count)
                    if not added:
                        # If inventory is full, we could drop items, but for simplicity just fail
                        return {
                            "success": False,
                            "error": "Inventory full, cannot pick up drops",
                        }

                # If breaking below player, decrease player height
                if (x, y, z) == self.get_position_below():
                    self.z -= 1

                return {"success": True, "consumed_tick": True, "drops": drops}
            else:
                return {"success": False, "error": "Block not found"}

        return {"success": True, "consumed_tick": True}

    def _generate_drops(self, block: Block) -> List[Tuple[ItemType, int]]:
        """Generate drops from a broken block"""
        import random

        if block.block_type == BlockType.SAPLING:
            return [(ItemType.SAPLING, 1)]
        elif block.block_type == BlockType.PLANK:
            return [(ItemType.PLANK, 1)]
        elif block.block_type == BlockType.LEAF:
            # 1-3 saplings
            count = random.randint(1, 3)
            return [(ItemType.SAPLING, count)]
        return []

    def _add_item_to_inventory(self, item_type: ItemType, count: int) -> bool:
        """Add item to inventory, returns True if successful"""
        remaining = count

        # First try to stack with existing items
        for slot in self.inventory:
            if remaining <= 0:
                break
            if slot.item and slot.item.item_type == item_type:
                can_add = min(remaining, slot.item.max_stack() - slot.item.count)
                if can_add > 0:
                    slot.item.count += can_add
                    remaining -= can_add

        # Then try empty slots
        for slot in self.inventory:
            if remaining <= 0:
                break
            if slot.is_empty():
                max_stack = Item(item_type, 1).max_stack()
                to_add = min(remaining, max_stack)
                slot.item = Item(item_type, to_add)
                remaining -= to_add

        return remaining <= 0

    def place_block(self, block_type_name: str) -> Dict[str, Any]:
        """Place a block from main hand. Costs 1 tick."""
        if not self.main_hand_item:
            return {"success": False, "error": "No item in main hand"}

        # Check if item is placeable
        try:
            if block_type_name.upper() == "SAPLING":
                block_type = BlockType.SAPLING
                item_type = ItemType.SAPLING
            elif block_type_name.upper() == "PLANK":
                block_type = BlockType.PLANK
                item_type = ItemType.PLANK
            else:
                return {"success": False, "error": "Cannot place this item type"}
        except ValueError:
            return {"success": False, "error": "Invalid block type"}

        if self.main_hand_item.item_type != item_type:
            return {
                "success": False,
                "error": "Main hand item doesn't match block type",
            }

        # Determine placement position
        facing_low = self.get_facing_block_position()
        facing_high = self.get_facing_block_position_high()
        below = self.get_position_below()

        # Check all possible positions
        possible_positions = [facing_low, facing_high, below]

        for pos in possible_positions:
            x, y, z = pos
            if not self.is_position_valid(x, y, z):
                continue

            if self.game_state.get_block(x, y, z) is not None:
                continue

            # Special checks for below position
            if pos == below:
                # Can only place if there's space above (height increase)
                if block_type == BlockType.SAPLING:
                    # Sapling can be placed at height 0
                    if z != 0:
                        continue
                    # Check if there's space for player height increase
                    if block_type.has_entity:
                        # Check if there's space above player for height increase
                        above_player = (self.x, self.y, self.z + self.height)
                        if self.game_state.get_block(*above_player):
                            continue
                else:
                    # For other blocks, check if player can stand on them
                    if block_type.has_entity:
                        # Check if there's space above player for height increase
                        above_player = (self.x, self.y, self.z + self.height)
                        if self.game_state.get_block(*above_player):
                            continue

            # Check adjacency requirement
            if not self.game_state.is_adjacent_to_block(x, y, z):
                continue

            # Place the block
            new_block = Block(block_type, x, y, z)
            if self.game_state.add_block(new_block):
                # Remove item from inventory
                self.main_hand_item.count -= 1
                if self.main_hand_item.count <= 0:
                    self.inventory[self.main_hand_slot].item = None

                # Special case: placing below player with entity increases height
                if pos == below and block_type.has_entity:
                    self.z += 1

                return {"success": True, "consumed_tick": True, "position": pos}

        return {"success": False, "error": "Cannot place block at any valid position"}

    def craft_axe(self) -> Dict[str, Any]:
        """Craft a wooden axe. Costs 2 ticks."""
        # Check if we have 3 planks
        plank_count = 0
        for slot in self.inventory:
            if slot.item and slot.item.item_type == ItemType.PLANK:
                plank_count += slot.item.count

        if plank_count < 3:
            return {"success": False, "error": "Not enough planks (need 3)"}

        # Check for empty slot or slot that can accept axe
        for slot in self.inventory:
            if slot.is_empty() or (
                slot.item and slot.item.item_type == ItemType.WOODEN_AXE
            ):
                # Remove 3 planks
                remaining = 3
                for inv_slot in self.inventory:
                    if remaining <= 0:
                        break
                    if inv_slot.item and inv_slot.item.item_type == ItemType.PLANK:
                        to_remove = min(remaining, inv_slot.item.count)
                        inv_slot.item.count -= to_remove
                        remaining -= to_remove
                        if inv_slot.item.count <= 0:
                            inv_slot.item = None

                # Add wooden axe
                if slot.is_empty():
                    slot.item = Item(ItemType.WOODEN_AXE, 1)
                else:
                    slot.item.count += 1

                return {"success": True, "consumed_ticks": 2}

        return {"success": False, "error": "No space for axe in inventory"}

    def get_inventory_state(self) -> List[Dict[str, Any]]:
        """Get current inventory state"""
        result = []
        for i, slot in enumerate(self.inventory):
            if slot.is_empty():
                result.append({"slot": i, "empty": True})
            else:
                result.append(
                    {
                        "slot": i,
                        "item_type": slot.item.item_type.value,
                        "count": slot.item.count,
                        "is_main_hand": i == self.main_hand_slot,
                    }
                )
        return result

    def get_state(self) -> Dict[str, Any]:
        """Get player state"""
        return {
            "position": (self.x, self.y, self.z),
            "direction": self.direction.name.lower(),
            "height": self.height,
            "inventory": self.get_inventory_state(),
            "breaking_block": self.breaking_block,
            "break_progress": self.break_progress,
        }
