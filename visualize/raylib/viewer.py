from __future__ import annotations

from typing import TYPE_CHECKING

import pyray as pr

from .camera import OrbitCamera
from .renderer import WorldRenderer, set_current_camera
from .hud import HUD
from .intent_source import ExternalIntentSource, HumanIntentSource, IntentSource

if TYPE_CHECKING:
    from game.game import Game

_WINDOW_W = 1280
_WINDOW_H = 720
_TARGET_FPS = 60


class RaylibViewer:
    """Main visualizer: owns the window, render loop, and tick orchestration.

    Thread safety guarantee: world state is only mutated by ``run()`` on the
    calling (main) thread.  ``ExternalIntentSource.submit()`` is the only
    cross-thread entry point and uses a thread-safe ``Queue``.
    """

    def __init__(
        self,
        game: Game,
        player_id: str,
        intent_source: IntentSource,
        title: str = "Smart Bot",
    ) -> None:
        self._game = game
        self._player_id = player_id
        self._source = intent_source
        self._title = title

        self._camera = OrbitCamera()
        self._renderer = WorldRenderer()
        self._hud = HUD()

    def run(self) -> None:
        """Open the window and block until it is closed."""
        pr.init_window(_WINDOW_W, _WINDOW_H, self._title)
        pr.set_target_fps(_TARGET_FPS)
        pr.set_exit_key(pr.KEY_ESCAPE)

        self._renderer.load()
        self._hud.load()

        try:
            self._loop()
        finally:
            self._renderer.unload()
            self._hud.unload()
            pr.close_window()

    # ── Main loop ────────────────────────────────────────────────────────────

    def _loop(self) -> None:
        while not pr.window_should_close():
            self._camera.update()

            player = self._game.world.get_player(self._player_id)
            camera = self._camera.get_camera()
            set_current_camera(camera)

            intent, should_tick = self._source.poll_frame(
                self._game.world,
                self._player_id,
                camera,
                self._renderer,
            )

            if should_tick:
                if intent is not None:
                    self._game.submit_player_intent(self._player_id, intent)
                self._game.tick()

            self._render(camera, player)

    # ── Rendering ────────────────────────────────────────────────────────────

    def _render(self, camera: pr.Camera3D, player) -> None:
        pr.begin_drawing()
        pr.clear_background(pr.Color(135, 206, 235, 255))  # sky blue fallback

        pr.begin_mode_3d(camera)
        self._renderer.draw(self._game.world, player, camera)
        pr.end_mode_3d()

        self._hud.draw(player, self._game, self._source.mode_name)
        pr.end_drawing()


# ── Factory functions ────────────────────────────────────────────────────────

def run_human_viewer(game: Game, player_id: str, title: str = "Smart Bot — Human") -> None:
    """Open a window where keyboard/mouse drives the player."""
    source = HumanIntentSource()
    RaylibViewer(game, player_id, source, title).run()


def run_ai_viewer(
    game: Game,
    player_id: str,
    source: ExternalIntentSource,
    title: str = "Smart Bot — AI",
) -> None:
    """Open a window in AI-controlled mode.

    The caller is responsible for submitting intents to ``source`` from a
    separate thread.  This function blocks until the window is closed.
    """
    RaylibViewer(game, player_id, source, title).run()
