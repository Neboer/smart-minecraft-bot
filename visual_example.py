#!/usr/bin/env python3
"""Visual demo: replays the example.py sequence at 1 step per second.

The AI thread submits intents; the Raylib main thread renders and ticks.
Run with:
    .venv\\Scripts\\python.exe visual_example.py
"""

from __future__ import annotations

import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game.core import BlockType, Item, ItemType
from game.game import Game
from game.intent import (
    ChangeActiveSlotIntent,
    CraftAxeIntent,
    DigIntent,
    DropOneIntent,
    DropStackIntent,
    NoIntent,
    PlaceBlockIntent,
    TurnIntent,
    WalkIntent,
)
from visualize.raylib import ExternalIntentSource, run_ai_viewer


def _ai_thread(game: Game, player_id: str, source: ExternalIntentSource) -> None:
    """Submits the example sequence with 1-second pauses between steps."""

    def step(intent, delay: float = 1.0) -> None:
        source.submit(intent)
        time.sleep(delay)

    player = game.world.get_player(player_id)
    assert player is not None

    time.sleep(0.5)  # let the window open

    # Walk east
    step(WalkIntent())

    # Turn south
    step(TurnIntent(direction="south"))

    # Walk south
    step(WalkIntent())

    # Change slot to 1
    step(ChangeActiveSlotIntent(1))

    # Change slot back to 0
    step(ChangeActiveSlotIntent(0))

    # Place a sapling at facing position (1, 0, 2)
    placed_pos = player.get_facing_block_position()
    step(PlaceBlockIntent(BlockType.SAPLING, placed_pos))

    # Give player planks for crafting
    player.inventory[0].item = Item(ItemType.PLANK, 3)

    # Craft wooden axe
    step(CraftAxeIntent())

    # Turn east and add a plank block to dig
    step(TurnIntent(direction="east"))
    target = (2, 0, 1)
    game.world.add_block(BlockType.PLANK, *target)

    # Dig plank (takes 2 hits with axe)
    step(DigIntent(target_position=target))

    safety = 6
    while player.breaking_block is not None and safety > 0:
        step(DigIntent())
        safety -= 1

    # Drop operations
    player.inventory[0].item = Item(ItemType.PLANK, 3)
    step(DropOneIntent())
    step(DropStackIntent())

    # Wait a moment then send a final NoIntent so the viewer stays alive
    time.sleep(2.0)
    step(NoIntent())


def main() -> None:
    game = Game()
    player_id, _ = game.world.create_player()

    source = ExternalIntentSource()

    ai = threading.Thread(target=_ai_thread, args=(game, player_id, source), daemon=True)
    ai.start()

    run_ai_viewer(game, player_id, source, title="Smart Bot — Visual Example")


if __name__ == "__main__":
    main()
