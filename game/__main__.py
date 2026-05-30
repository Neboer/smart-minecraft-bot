#!/usr/bin/env python3
"""
Game main module - allows running the game as a module
"""
from .game import Game

def main():
    """Main entry point for the game"""
    print("Smart Bot Game")
    print("==============")
    
    # Create game/world
    game = Game()
    world = game.world
    
    # Create a player
    player_id, player = world.create_player()
    
    print(f"Player {player_id} created at {player.get_state()['position']}")
    print(f"Facing {player.get_state()['direction']}")
    print(f"Inventory: {player.get_inventory_state()}")
    
    print("\nGame ready! Submit intents into Game and then call game.tick().")
    print("Example:")
    print("  game.submit_player_intent(player_id, WalkIntent())")
    print("  game.tick()")
    print("  game.submit_player_intent(player_id, TurnIntent('north'))")
    print("  game.tick()")
    print("  game.submit_player_intent(player_id, PlaceIntent('sapling'))")
    print("  game.tick()")
    
    return game, player_id, player

if __name__ == "__main__":
    main()
