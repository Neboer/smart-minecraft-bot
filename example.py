#!/usr/bin/env python3
"""Example script that runs a small smoke-test suite for the player intent flow.

The world starts empty and the player starts with one sapling in the main hand.
"""

from __future__ import annotations

import os
import sys
import threading
import time
from itertools import cycle

# Add the project root to the Python path.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game.core import BlockType, Item, ItemType
from game.intents import CraftAxeIntent, DigIntent, NoIntent, PlaceIntent, SwapInventoryIntent, TurnIntent, WalkIntent
from game.game import Game
from game.player import Player
from visualize import run_visualizer


def build_empty_game() -> tuple[Game, str, Player]:
    """Create an empty world with one player holding a sapling."""
    game = Game()
    player_id, player = game.world.create_player()
    return game, player_id, player


def submit_and_tick(game: Game, player_id: str, intent) -> dict:
    game.submit_player_intent(player_id, intent)
    return game.tick()


def _print_check(name: str, condition: bool, verbose: bool) -> None:
    if verbose:
        print(f"[ok] {name}" if condition else f"[fail] {name}")
    assert condition, name


def run_player_smoke_tests(verbose: bool = True) -> None:
    """Run a simple smoke-test suite that covers the intent pipeline."""
    game, player_id, player = build_empty_game()

    # Initial state checks.
    _print_check("world starts empty", game.world.get_world_state()["blocks"] == [], verbose)
    _print_check("player starts at origin", (player.x, player.y, player.z) == (0, 0, 0), verbose)
    _print_check("player faces east", player.direction.name.lower() == "east", verbose)
    _print_check("player height is 2", player.height == 2, verbose)
    _print_check("main hand starts with sapling", player.main_hand_item.item_type == ItemType.SAPLING, verbose)
    _print_check("inventory slot 0 contains sapling", player.inventory[0].item.item_type == ItemType.SAPLING, verbose)
    _print_check("facing position is east", player.get_facing_block_position() == (1, 0, 0), verbose)
    _print_check("nearby blocks initially empty", game.world.get_blocks_in_range(0, 0, 0, 2) == [], verbose)

    # Movement and turning.
    move_result = submit_and_tick(game, player_id, WalkIntent())
    _print_check("move forward advances one tick", move_result["tick"] == 1, verbose)
    _print_check("move forward changes position", (player.x, player.y, player.z) == (1, 0, 0), verbose)

    turn_result = submit_and_tick(game, player_id, TurnIntent(direction="south"))
    _print_check("turn south advances one tick", turn_result["tick"] == 2, verbose)
    _print_check("turn south changes direction", player.direction.name.lower() == "south", verbose)

    move_south = submit_and_tick(game, player_id, WalkIntent())
    _print_check("second move advances one tick", move_south["tick"] == 3, verbose)
    _print_check("second move changes position", (player.x, player.y, player.z) == (1, 1, 0), verbose)

    # Swap inventory slots.
    swap_result = submit_and_tick(game, player_id, SwapInventoryIntent(slot1=0, slot2=1))
    _print_check("swap advances one tick", swap_result["tick"] == 4, verbose)
    _print_check("slot 0 becomes empty after swap", player.inventory[0].is_empty(), verbose)
    _print_check("slot 1 receives the sapling", player.inventory[1].item.item_type == ItemType.SAPLING, verbose)

    # Restore the sapling to main hand so we can place a block.
    player.inventory[0].item = Item(ItemType.SAPLING, 1)
    player.inventory[1].item = None

    place_result = submit_and_tick(game, player_id, PlaceIntent(block_type_name="sapling"))
    _print_check("place block advances one tick", place_result["tick"] == 5, verbose)
    placed_position = (1, 2, 0)
    _print_check(
        "sapling block was placed",
        game.world.game_state.get_block(*placed_position) is not None,
        verbose,
    )
    _print_check("main hand consumed the sapling", player.main_hand_item is None, verbose)
    _print_check("world state now has blocks", len(game.world.get_world_state()["blocks"]) >= 1, verbose)
    _print_check("nearby blocks now visible", len(game.world.get_blocks_in_range(player.x, player.y, player.z, 3)) >= 1, verbose)

    # Restock the inventory and craft an axe.
    player.inventory[0].item = Item(ItemType.PLANK, 3)
    craft_result = submit_and_tick(game, player_id, CraftAxeIntent())
    _print_check("craft axe advances one tick", craft_result["tick"] == 6, verbose)
    _print_check(
        "wooden axe is in main hand",
        player.main_hand_item is not None and player.main_hand_item.item_type == ItemType.WOODEN_AXE,
        verbose,
    )

    # Digging: add a plank block and break it over multiple ticks.
    submit_and_tick(game, player_id, TurnIntent(direction="east"))
    target = (2, 1, 0)
    _print_check("facing east for digging", player.get_facing_block_position() == target, verbose)
    game.world.add_block(BlockType.PLANK, *target)
    _print_check("plank added for digging", game.world.game_state.get_block(*target) is not None, verbose)

    start_break = submit_and_tick(game, player_id, DigIntent(target_position=target))
    _print_check("start breaking advances one tick", start_break["tick"] == 8, verbose)
    _print_check("player is breaking the plank", player.breaking_block == target, verbose)

    expected_tick = 8
    safety_limit = 6
    while player.breaking_block is not None and safety_limit > 0:
        expected_tick += 1
        continue_break = submit_and_tick(game, player_id, DigIntent())
        _print_check(
            f"continue breaking advances tick {expected_tick}",
            continue_break["tick"] == expected_tick,
            verbose,
        )
        safety_limit -= 1

    _print_check("digging finished within the safety limit", safety_limit > 0, verbose)

    _print_check("plank was removed after digging", game.world.game_state.get_block(*target) is None, verbose)
    _print_check("digging state cleared", player.breaking_block is None, verbose)
    _print_check("world tick count advanced", game.world.get_world_state()["tick"] == expected_tick, verbose)

    if verbose:
        print("\nAll player smoke tests passed.")


def run_preview_mode() -> None:
    """Open the visualizer and stream one intent per second into the game."""
    game, player_id, player = build_empty_game()
    action_cycle = cycle([
        WalkIntent(),
        TurnIntent(direction="south"),
        WalkIntent(),
        TurnIntent(direction="west"),
        WalkIntent(),
        NoIntent(),
    ])

    stop_event = threading.Event()

    def submit_actions() -> None:
        for intent in action_cycle:
            if stop_event.is_set():
                return
            game.submit_player_intent(player_id, intent)
            time.sleep(1.0)

    thread = threading.Thread(target=submit_actions, daemon=True)
    thread.start()
    try:
        run_visualizer(game.world, player, game)
    finally:
        stop_event.set()


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1].lower() == "preview":
        print("=== Smart Bot Preview Mode ===\n")
        run_preview_mode()
        return

    print("=== Smart Bot Player Smoke Tests ===\n")
    run_player_smoke_tests(verbose=True)


if __name__ == "__main__":
    main()
