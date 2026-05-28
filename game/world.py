from typing import List, Dict, Tuple, Optional, Any
from .core import GameState, Block, BlockType, Direction
from .player import Player

class World:
    def __init__(self):
        self.game_state = GameState()
        self.players: Dict[str, Player] = {}
        self.player_counter = 0
    
    def create_player(self, player_id: Optional[str] = None) -> Tuple[str, Player]:
        """Create a new player in the world"""
        if player_id is None:
            self.player_counter += 1
            player_id = f"player_{self.player_counter}"
        
        player = Player(self.game_state)
        self.players[player_id] = player
        return player_id, player
    
    def get_player(self, player_id: str) -> Optional[Player]:
        """Get a player by ID"""
        return self.players.get(player_id)
    
    def remove_player(self, player_id: str) -> bool:
        """Remove a player from the world"""
        if player_id in self.players:
            del self.players[player_id]
            return True
        return False
    
    def process_tick(self) -> Dict[str, Any]:
        """Process one tick for the entire world"""
        # Process world simulation (tree growth, etc.)
        self.game_state.process_tick()
        
        # Update player breaking progress
        results = {}
        for player_id, player in self.players.items():
            if player.breaking_block:
                # Breaking continues automatically each tick
                result = player.continue_breaking_block()
                results[player_id] = result
        
        return {
            "tick": self.game_state.tick_count,
            "player_updates": results
        }
    
    def get_world_state(self) -> Dict[str, Any]:
        """Get the entire world state"""
        blocks = []
        for (x, y, z), block in self.game_state.blocks.items():
            blocks.append({
                "position": (x, y, z),
                "type": block.block_type.value,
                "has_entity": block.has_entity
            })
        
        players = {}
        for player_id, player in self.players.items():
            players[player_id] = player.get_state()
        
        return {
            "tick": self.game_state.tick_count,
            "world_size": self.game_state.world_size,
            "blocks": blocks,
            "players": players
        }
    
    def get_blocks_in_range(self, x: int, y: int, z: int, radius: int) -> List[Dict[str, Any]]:
        """Get all blocks within a certain radius of a position"""
        result = []
        for (bx, by, bz), block in self.game_state.blocks.items():
            if abs(bx - x) <= radius and abs(by - y) <= radius and abs(bz - z) <= radius:
                result.append({
                    "position": (bx, by, bz),
                    "type": block.block_type.value,
                    "has_entity": block.has_entity
                })
        return result
    
    def add_block(self, block_type: BlockType, x: int, y: int, z: int) -> bool:
        """Add a block to the world (for testing or admin purposes)"""
        block = Block(block_type, x, y, z)
        return self.game_state.add_block(block)
    
    def remove_block(self, x: int, y: int, z: int) -> bool:
        """Remove a block from the world (for testing or admin purposes)"""
        block = self.game_state.remove_block(x, y, z)
        return block is not None
