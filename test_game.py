#!/usr/bin/env python3
"""
Simple test script for the game
"""
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game.world import World
from game.api import PlayerAPI

def test_basic_functionality():
    """Test basic game functionality"""
    print("Creating world and player...")
    world = World()
    player_id, player = world.create_player()
    api = PlayerAPI(world, player_id)
    
    print(f"Player created with ID: {player_id}")
    print(f"Initial position: {api.get_position()}")
    print(f"Initial direction: {api.get_direction()}")
    print(f"Initial inventory: {api.get_inventory()}")
    
    # Test movement
    print("\nTesting movement...")
    result = api.move_forward()
    print(f"Move forward: {result}")
    print(f"New position: {api.get_position()}")
    
    # Test turning
    print("\nTesting turning...")
    result = api.turn("north")
    print(f"Turn north: {result}")
    print(f"New direction: {api.get_direction()}")
    
    # Test placing block
    print("\nTesting placing block...")
    result = api.place_block("sapling")
    print(f"Place sapling: {result}")
    
    # Test world state
    print("\nGetting world state...")
    world_state = api.get_world_state()
    print(f"World tick: {world_state['tick']}")
    print(f"Number of blocks: {len(world_state['blocks'])}")
    
    # Test inventory
    print("\nTesting inventory...")
    inventory = api.get_inventory()
    print(f"Inventory: {inventory}")
    
    print("\nBasic tests completed!")

if __name__ == "__main__":
    test_basic_functionality()
