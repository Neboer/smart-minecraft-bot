from typing import Dict, Any, Optional, List
from ..player import Player
from ..world import World

class PlayerAPI:
    """API interface for player actions"""
    
    def __init__(self, world: World, player_id: str):
        self.world = world
        self.player_id = player_id
        self.player = world.get_player(player_id)
        if not self.player:
            raise ValueError(f"Player {player_id} not found")
    
    def move_forward(self) -> Dict[str, Any]:
        """Move forward one block in current direction. Costs 1 tick."""
        result = self.player.move_forward()
        if result.get("success") and result.get("consumed_tick"):
            self.world.process_tick()
        return result
    
    def turn(self, direction: str) -> Dict[str, Any]:
        """Turn to face a direction (north, south, east, west). Costs 1 tick."""
        result = self.player.turn_to(direction)
        if result.get("success") and result.get("consumed_tick"):
            self.world.process_tick()
        return result
    
    def start_breaking(self, x: int, y: int, z: int) -> Dict[str, Any]:
        """Start breaking a block at position. Costs 1 tick."""
        result = self.player.start_breaking_block(x, y, z)
        if result.get("success") and result.get("consumed_tick"):
            self.world.process_tick()
        return result
    
    def continue_breaking(self) -> Dict[str, Any]:
        """Continue breaking the current block. Costs 1 tick."""
        result = self.player.continue_breaking_block()
        if result.get("success") and result.get("consumed_tick"):
            self.world.process_tick()
        return result
    
    def place_block(self, block_type: str) -> Dict[str, Any]:
        """Place a block from main hand. Costs 1 tick."""
        result = self.player.place_block(block_type)
        if result.get("success") and result.get("consumed_tick"):
            self.world.process_tick()
        return result
    
    def craft_axe(self) -> Dict[str, Any]:
        """Craft a wooden axe from 3 planks. Costs 2 ticks."""
        result = self.player.craft_axe()
        if result.get("success") and "consumed_ticks" in result:
            # Consume the specified number of ticks
            for _ in range(result["consumed_ticks"]):
                self.world.process_tick()
        return result
    
    def swap_inventory_slots(self, slot1: int, slot2: int) -> Dict[str, Any]:
        """Swap items between two inventory slots. Does not consume tick."""
        return self.player.swap_inventory_slots(slot1, slot2)
    
    def get_inventory(self) -> Dict[str, Any]:
        """Get current inventory state"""
        return {"inventory": self.player.get_inventory_state()}
    
    def get_player_state(self) -> Dict[str, Any]:
        """Get player state including position, direction, etc."""
        return self.player.get_state()
    
    def get_world_state(self) -> Dict[str, Any]:
        """Get the entire world state"""
        return self.world.get_world_state()
    
    def get_nearby_blocks(self, radius: int = 3) -> Dict[str, Any]:
        """Get blocks within a certain radius of the player"""
        blocks = self.world.get_blocks_in_range(
            self.player.x, 
            self.player.y, 
            self.player.z, 
            radius
        )
        return {"blocks": blocks}
    
    def get_facing_position(self) -> Dict[str, Any]:
        """Get the position of the block in front of the player"""
        pos = self.player.get_facing_block_position()
        return {"position": pos}
    
    def get_position(self) -> Dict[str, Any]:
        """Get player's current position"""
        return {"position": (self.player.x, self.player.y, self.player.z)}
    
    def get_direction(self) -> Dict[str, Any]:
        """Get player's current direction"""
        return {"direction": self.player.direction.name.lower()}
    
    def get_height(self) -> Dict[str, Any]:
        """Get player's current height"""
        return {"height": self.player.height}
    
    def get_main_hand_item(self) -> Dict[str, Any]:
        """Get the item in main hand (slot 0)"""
        item = self.player.main_hand_item
        if item:
            return {
                "item_type": item.item_type.value,
                "count": item.count
            }
        return {"empty": True}
