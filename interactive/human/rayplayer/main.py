"""Entry point for the human-controlled Raylib game client."""

from __future__ import annotations

import os
import sys

# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from game.game import Game
from visualize.raylib import run_human_viewer


def start() -> None:
    game = Game()
    player_id, _ = game.world.create_player()
    run_human_viewer(game, player_id)


if __name__ == "__main__":
    start()
