#!/usr/bin/env python3
"""Smoke-test suite for the player intent flow.

The world starts empty and the player starts with one sapling in the main hand.
"""

from __future__ import annotations

import os
import sys
import threading
import time
from itertools import cycle

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game.core import BlockType, Item, ItemType
from game.intent import (
    BaseIntent,
    ChangeActiveSlotIntent,
    CraftAxeIntent,
    DigIntent,
    DropOneIntent,
    DropStackIntent,
    PlaceBlockIntent,
    TurnIntent,
    WalkIntent,
)
from game.game import Game
from game.player import Player


def build_empty_game() -> tuple[Game, str, Player]:
    game = Game()
    player_id, player = game.world.create_player()
    return game, player_id, player


def submit_and_tick(game: Game, player_id: str, intent: BaseIntent) -> None:
    game.submit_player_intent(player_id, intent)
    game.tick()


def _check(name: str, condition: bool, verbose: bool) -> None:
    if verbose:
        print(f"[ok] {name}" if condition else f"[FAIL] {name}")
    assert condition, name


def run_player_smoke_tests(verbose: bool = True) -> None:
    game, player_id, player = build_empty_game()

    _check("world starts empty", game.world.get_world_state()["blocks"] == [], verbose)
    _check("player starts at origin", (player.x, player.y, player.z) == (0, 0, 0), verbose)
    _check("player faces east", player.direction.name.lower() == "east", verbose)
    _check("player height is 2", player.height == 2, verbose)
    _check("main hand starts with sapling", player.main_hand_item.item_type == ItemType.SAPLING, verbose)
    _check("inventory slot 0 has sapling", player.inventory[0].item.item_type == ItemType.SAPLING, verbose)
    _check("facing position is east", player.get_facing_block_position() == (1, 0, 0), verbose)
    _check("nearby blocks initially empty", game.world.get_blocks_in_range(0, 0, 0, 2) == [], verbose)

    # Movement and turning
    submit_and_tick(game, player_id, WalkIntent())
    _check("move forward tick 1", game.world.game_state.tick_count == 1, verbose)
    _check("move forward changes position", (player.x, player.y, player.z) == (1, 0, 0), verbose)

    submit_and_tick(game, player_id, TurnIntent(direction="south"))
    _check("turn south tick 2", game.world.game_state.tick_count == 2, verbose)
    _check("turn south changes direction", player.direction.name.lower() == "south", verbose)

    submit_and_tick(game, player_id, WalkIntent())
    _check("second move tick 3", game.world.game_state.tick_count == 3, verbose)
    _check("second move changes position", (player.x, player.y, player.z) == (1, 0, 1), verbose)

    # Change active slot (0-tick intent)
    submit_and_tick(game, player_id, ChangeActiveSlotIntent(1))
    _check("change slot tick 4", game.world.game_state.tick_count == 4, verbose)
    _check("active slot is 1", player.main_hand_slot == 1, verbose)
    _check("main hand empty after slot change", player.main_hand_item is None, verbose)
    _check("slot 0 still has sapling", player.inventory[0].item.item_type == ItemType.SAPLING, verbose)

    submit_and_tick(game, player_id, ChangeActiveSlotIntent(0))
    _check("change slot back tick 5", game.world.game_state.tick_count == 5, verbose)
    _check("active slot is 0", player.main_hand_slot == 0, verbose)
    _check("main hand has sapling", player.main_hand_item.item_type == ItemType.SAPLING, verbose)

    # Place block — player is at (1,1,0) facing south; facing position is (1,2,0)
    placed_position = player.get_facing_block_position()
    submit_and_tick(game, player_id, PlaceBlockIntent(BlockType.SAPLING, placed_position))
    _check("place block tick 6", game.world.game_state.tick_count == 6, verbose)
    placed_position = (1, 0, 2)
    _check(
        "sapling placed",
        game.world.game_state.get_block(*placed_position) is not None,
        verbose,
    )
    _check("main hand consumed", player.main_hand_item is None, verbose)
    _check("world has blocks", len(game.world.get_world_state()["blocks"]) >= 1, verbose)
    _check("blocks visible in range", len(game.world.get_blocks_in_range(player.x, player.y, player.z, 3)) >= 1, verbose)

    # Craft axe
    player.inventory[0].item = Item(ItemType.PLANK, 3)
    submit_and_tick(game, player_id, CraftAxeIntent())
    _check("craft axe tick 7", game.world.game_state.tick_count == 7, verbose)
    _check(
        "wooden axe in main hand",
        player.main_hand_item is not None and player.main_hand_item.item_type == ItemType.WOODEN_AXE,
        verbose,
    )

    # Digging: add a plank block and break it
    submit_and_tick(game, player_id, TurnIntent(direction="east"))
    target = (2, 0, 1)
    _check("facing east for digging", player.get_facing_block_position() == target, verbose)
    game.world.add_block(BlockType.PLANK, *target)
    _check("plank added for digging", game.world.game_state.get_block(*target) is not None, verbose)

    submit_and_tick(game, player_id, DigIntent(target_position=target))
    _check("start breaking tick 9", game.world.game_state.tick_count == 9, verbose)
    _check("player breaking plank", player.breaking_block == target, verbose)

    expected_tick = 9
    safety_limit = 6
    while player.breaking_block is not None and safety_limit > 0:
        expected_tick += 1
        submit_and_tick(game, player_id, DigIntent())
        _check(
            f"continue breaking tick {expected_tick}",
            game.world.game_state.tick_count == expected_tick,
            verbose,
        )
        safety_limit -= 1

    _check("digging finished within safety limit", safety_limit > 0, verbose)
    _check("plank removed after digging", game.world.game_state.get_block(*target) is None, verbose)
    _check("dig state cleared", player.breaking_block is None, verbose)
    _check("tick count correct", game.world.game_state.tick_count == expected_tick, verbose)

    # Drop one item
    player.inventory[0].item = Item(ItemType.PLANK, 3)
    submit_and_tick(game, player_id, DropOneIntent())
    _check("drop one decrements count", player.inventory[0].item is not None and player.inventory[0].item.count == 2, verbose)

    # Drop full stack
    submit_and_tick(game, player_id, DropStackIntent())
    _check("drop stack clears slot", player.inventory[0].is_empty(), verbose)

    # Pillar-up: place a plank at own feet to raise player by 1
    player.inventory[0].item = Item(ItemType.PLANK, 1)
    pillar_from = player.get_position()          # (1, 0, 1)
    submit_and_tick(game, player_id, PlaceBlockIntent(BlockType.PLANK, pillar_from))
    _check(
        "pillar block placed at old feet",
        game.world.game_state.get_block(*pillar_from) is not None,
        verbose,
    )
    _check(
        "player raised by 1 after pillar",
        (player.x, player.y, player.z) == (pillar_from.x, pillar_from.y + 1, pillar_from.z),
        verbose,
    )
    _check("player has support after pillar", player.y > 0, verbose)

    if verbose:
        print("\nAll smoke tests passed.")


# def run_preview_mode() -> None:
#     game, player_id, player = build_empty_game()
#     action_cycle = cycle([
#         WalkIntent(),
#         TurnIntent(direction="south"),
#         WalkIntent(),
#         TurnIntent(direction="west"),
#         WalkIntent(),
#         NoIntent(),
#     ])

#     stop_event = threading.Event()

#     def submit_actions() -> None:
#         for intent in action_cycle:
#             if stop_event.is_set():
#                 return
#             game.submit_player_intent(player_id, intent)
#             time.sleep(1.0)

#     thread = threading.Thread(target=submit_actions, daemon=True)
#     thread.start()
#     try:
#         run_visualizer(game.world, player, game)
#     finally:
#         stop_event.set()


def main() -> None:
    # if len(sys.argv) > 1 and sys.argv[1].lower() == "preview":
    #     print("=== Smart Bot Preview Mode ===\n")
    #     run_preview_mode()
    #     return
    print("=== Smart Bot Player Smoke Tests ===\n")
    run_player_smoke_tests(verbose=True)


if __name__ == "__main__":
    main()
