#!/usr/bin/env python3
"""
Game main module - allows running the game as a module
"""
from .game import Game
from .api import PlayerAPI

def main():
    """Main entry point for the game"""
    print("Smart Bot Game")
    print("==============")
    
    # Create game/world
    game = Game()
    world = game.world
    
    # Create a player
    player_id, player = world.create_player()
    api = PlayerAPI(game, player_id)
    
    print(f"Player {player_id} created at {api.get_position()}")
    print(f"Facing {api.get_direction()}")
    print(f"Inventory: {api.get_inventory()}")
    
    print("\nGame ready! Use the PlayerAPI to interact with the world.")
    print("Example:")
    print("  api.move_forward()")
    print("  api.turn('north')")
    print("  api.place_block('sapling')")
    
    return game, api

if __name__ == "__main__":
    main()
