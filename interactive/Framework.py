import threading
import time

import game
from game.game import Game
from game.intent import BaseIntent
from game.player import Player
from visualize.viewer import run_visualizer


class Bot:
    """Base class for bots. Subclass this and implement the propose_intent method."""

    def __init__(self, game: Game, player_id: str, player: Player):
        # readonly game object.
        self.game = game
        self.player_id = player_id
        self.player = player

    # method to implement need override
    def propose_intent(self) -> BaseIntent:
        """Propose an intent for the given game state and player ID."""
        raise NotImplementedError("propose_intent must be implemented by subclasses")


# def run_bot(bot: Bot):
#     """Run the bot in the game loop."""
#     while True:
#         intent = bot.propose_intent()
#         bot.game.submit_player_intent(bot.player_id, intent)
#         bot.game.tick()


def run_bot_with_visualizer(bot_class: type[Bot]):
    """Run the bot with the visualizer."""
    game = Game()
    player_id, player = game.world.create_player()
    bot = bot_class(game, player_id, player)

    stop_event = threading.Event()

    def bot_thread() -> None:
        while not stop_event.is_set():
            if stop_event.is_set():
                return
            game.submit_player_intent(player_id, bot.propose_intent())
            time.sleep(1.0)
    thread = threading.Thread(target=bot_thread, daemon=True)
    thread.start()

    try:
        run_visualizer(game.world, player, game)
    finally:
        stop_event.set()
