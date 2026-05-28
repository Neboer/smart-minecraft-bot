#!/usr/bin/env python3
"""
Example script demonstrating game API usage
"""
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game.game import Game
from game.api import PlayerAPI

def main():
    print("=== Smart Bot Game Example ===\n")
    
    # Create world and player
    print("1. Creating world and player...")
    game = Game()
    player_id, player = game.world.create_player()
    api = PlayerAPI(game, player_id)
    
    print(f"   Player ID: {player_id}")
    print(f"   Initial position: {api.get_position()}")
    print(f"   Initial direction: {api.get_direction()}")
    print(f"   Initial inventory: {api.get_inventory()}")
    
    # Move forward
    print("\n2. Moving forward...")
    result = api.move_forward()
    if result["success"]:
        print("   ✓ Moved forward successfully")
        print(f"   New position: {api.get_position()}")
    else:
        print(f"   ✗ Failed to move: {result['error']}")
    
    # Turn north
    print("\n3. Turning north...")
    result = api.turn("north")
    if result["success"]:
        print("   ✓ Turned north successfully")
        print(f"   New direction: {api.get_direction()}")
    else:
        print(f"   ✗ Failed to turn: {result['error']}")
    
    # Place sapling (should fail - no block adjacent)
    print("\n4. Trying to place sapling (should fail - no adjacent block)...")
    result = api.place_block("sapling")
    if result["success"]:
        print("   ✓ Placed sapling successfully")
    else:
        print(f"   ✗ Failed to place: {result['error']}")
    
    # Check world state
    print("\n5. Checking world state...")
    world_state = api.get_world_state()
    print(f"   World tick: {world_state['tick']}")
    print(f"   Number of blocks: {len(world_state['blocks'])}")
    print(f"   Number of players: {len(world_state['players'])}")
    
    # Get nearby blocks
    print("\n6. Getting nearby blocks...")
    nearby = api.get_nearby_blocks(radius=2)
    print(f"   Blocks within radius 2: {len(nearby['blocks'])}")
    
    # Swap inventory slots
    print("\n7. Swapping inventory slots 0 and 1...")
    result = api.swap_inventory_slots(0, 1)
    if result["success"]:
        print("   ✓ Swapped slots successfully")
        print(f"   New inventory: {api.get_inventory()}")
    else:
        print(f"   ✗ Failed to swap: {result['error']}")
    
    # Swap back
    print("\n8. Swapping back to original positions...")
    api.swap_inventory_slots(0, 1)
    
    print("\n=== Example completed ===")
    print("\nPlayer API provides the following methods:")
    print("- move_forward()")
    print("- turn(direction)")
    print("- start_breaking(x, y, z)")
    print("- continue_breaking()")
    print("- place_block(block_type)")
    print("- craft_axe()")
    print("- swap_inventory_slots(slot1, slot2)")
    print("- get_inventory()")
    print("- get_player_state()")
    print("- get_world_state()")
    print("- get_nearby_blocks(radius)")
    print("- get_facing_position()")
    print("- get_position()")
    print("- get_direction()")
    print("- get_height()")
    print("- get_main_hand_item()")

if __name__ == "__main__":
    main()
