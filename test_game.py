#!/usr/bin/env python3
"""
World visualizer demo (Moderngl).
"""
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game.game import Game
from game.core import BlockType
from visualize import run_visualizer


def run_visual_demo() -> None:
    game = Game()
    player_id, player = game.world.create_player()

    # Simple scene setup
    game.world.add_block(BlockType.PLANK, 2, 2, 0)
    game.world.add_block(BlockType.PLANK, 2, 2, 1)
    game.world.add_block(BlockType.LEAF, 2, 2, 2)
    game.world.add_block(BlockType.SAPLING, 1, 3, 0)

    run_visualizer(game.world, player, game)


if __name__ == "__main__":
    run_visual_demo()
