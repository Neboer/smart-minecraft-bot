from __future__ import annotations

import sys
import threading
import time
from typing import Optional, TextIO

from game.game import Game
from game.intent import BaseIntent, NoIntent
from game.player import Player
from interactive.Framework import Bot
from visualize.viewer import run_visualizer

from .commands import HELP_TEXT, ParseError, format_status, parse_line


class REPLPlayer(Bot):
    """Interactive human player driven by a command-line REPL.

    Interactive mode (default): reads from stdin with a '>' prompt.
    File mode (input_file given): reads commands line-by-line from a text file;
      optionally sleeps sleep_between seconds after each tick.
    """

    def __init__(
        self,
        game: Game,
        player_id: str,
        player: Player,
        input_file: Optional[str] = None,
        sleep_between: float = 0.0,
    ) -> None:
        super().__init__(game, player_id, player)
        self._from_file = input_file is not None
        self._stream: TextIO = open(input_file, encoding="utf-8") if input_file else sys.stdin
        self._sleep_between = sleep_between
        self._quit = False

    # ── Input ──────────────────────────────────────────────────────────────

    def _read_line(self) -> str | None:
        """Read one raw line. Returns None on EOF."""
        if self._from_file:
            line = self._stream.readline()
            if not line:
                return None
            print(f"> {line.rstrip()}")
            return line
        try:
            return input("> ")
        except EOFError:
            return None

    # ── Bot interface ───────────────────────────────────────────────────────

    def propose_intent(self) -> BaseIntent:
        """Block until a game-advancing command is ready, then return its intent.

        Non-ticking commands (status, help) are handled in-place and the loop
        continues. Returns NoIntent and sets _quit=True on EOF or quit/exit.
        """
        while True:
            line = self._read_line()
            if line is None:
                self._quit = True
                return NoIntent()

            try:
                result = parse_line(line, self.player)
            except ParseError as exc:
                print(f"Error: {exc}")
                continue

            if result == "":
                continue
            if result == "quit":
                self._quit = True
                return NoIntent()
            if result == "status":
                print(format_status(self.player))
                continue
            if result == "help":
                print(HELP_TEXT)
                continue
            return result  # type: ignore[return-value]

    # ── Runners ─────────────────────────────────────────────────────────────

    def run(self) -> None:
        """Run without the visualizer: each command advances exactly one game tick."""
        print("Smart Bot REPL — type 'help' for commands, 'quit' to exit.\n")
        while not self._quit:
            intent = self.propose_intent()
            if self._quit:
                break
            self.game.submit_player_intent(self.player_id, intent)
            self.game.tick()
            if self._sleep_between > 0:
                time.sleep(self._sleep_between)
        print("Goodbye.")

    def run_with_visualizer(self) -> None:
        """Run with the 3D visualizer.

        The REPL controls ticking (one tick per command) on a worker thread.
        The visualizer renders on the main thread, refreshing from the shared
        world state each frame (game=None so the renderer does not auto-tick).
        """
        print("Smart Bot REPL + Visualizer — type 'help' for commands, 'quit' to exit.\n")
        world_lock = threading.Lock()
        stop_event = threading.Event()

        def _repl_loop() -> None:
            while not self._quit and not stop_event.is_set():
                intent = self.propose_intent()
                if self._quit or stop_event.is_set():
                    break
                with world_lock:
                    self.game.submit_player_intent(self.player_id, intent)
                    self.game.tick()
                if self._sleep_between > 0:
                    time.sleep(self._sleep_between)

        thread = threading.Thread(target=_repl_loop, daemon=True)
        thread.start()
        try:
            # game=None → visualizer sets _auto_refresh=True and rebuilds the
            # scene every frame from the live world state without auto-ticking.
            run_visualizer(self.game.world, self.player, game=None, world_lock=world_lock)
        finally:
            stop_event.set()
            self._quit = True
        print("Goodbye.")


def main(
    input_file: Optional[str] = None,
    sleep_between: float = 0.0,
    with_visualizer: bool = False,
) -> None:
    """Create a game, attach a REPL player, and run."""
    g = Game()
    player_id, player = g.world.create_player()
    repl = REPLPlayer(g, player_id, player, input_file, sleep_between)
    if with_visualizer:
        repl.run_with_visualizer()
    else:
        repl.run()
