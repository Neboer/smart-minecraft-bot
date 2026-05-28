#!/usr/bin/env python3
"""
Example script demonstrating game API usage
"""

import sys
import os
import threading
import time
from itertools import cycle

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game.game import Game
from game.core import BlockType
from game.api import PlayerAPI
from visualize import run_visualizer


def main() -> None:
    print("=== Smart Bot Game Visual Example ===\n")

    game = Game()
    player_id, player_entity = game.world.create_player()
    player = PlayerAPI(game, player_id)

    world_lock = threading.Lock()

    with world_lock:
        game.world.add_block(BlockType.PLANK, 2, 2, 0)
        game.world.add_block(BlockType.PLANK, 2, 2, 1)
        game.world.add_block(BlockType.LEAF, 2, 2, 2)
        game.world.add_block(BlockType.SAPLING, 1, 3, 0)

    render_thread = threading.Thread(
        target=run_visualizer,
        args=(game.world, player_entity, None, world_lock),
        daemon=True,
    )
    render_thread.start()

    actions = cycle([
        ("move forward", lambda: player.move_forward()),
        ("move forward", lambda: player.move_forward()),
        ("turn south", lambda: player.turn("south")),
        ("move forward", lambda: player.move_forward()),
        ("turn west", lambda: player.turn("west")),
        ("move forward", lambda: player.move_forward()),
        ("turn north", lambda: player.turn("north")),
        ("move forward", lambda: player.move_forward()),
    ])

    tick_index = 0
    print("Renderer started on another thread. Running one action per second...\n")

    try:
        while True:
            tick_index += 1
            action_name, action_fn = next(actions)
            with world_lock:
                result = action_fn()
                position = player.get_position()["position"]
                direction = player.get_direction()["direction"]
            success = result.get("success", False)
            status = "✓" if success else "✗"
            error = f" (error: {result.get('error')})" if not success else ""
            print(
                f"[tick {tick_index:02d}] {status} {action_name}{error} -> "
                f"pos={position}, dir={direction}"
            )
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
