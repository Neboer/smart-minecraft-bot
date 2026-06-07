from __future__ import annotations

from abc import ABC, abstractmethod
from queue import Empty, Queue
from typing import Optional, TYPE_CHECKING

import pyray as pr

from game.core import Vec3I
from game.intent import (
    BaseIntent,
    ChangeActiveSlotIntent,
    DigIntent,
    NoIntent,
    PlaceBlockIntent,
    TurnIntent,
    WalkIntent,
)

if TYPE_CHECKING:
    from game.world import World
    from game.player import Player
    from visualize.raylib.renderer import WorldRenderer


class IntentSource(ABC):
    """Decides what intent to submit and whether to advance a tick this frame."""

    @abstractmethod
    def poll_frame(
        self,
        world: World,
        player_id: str,
        camera: pr.Camera3D,
        renderer: WorldRenderer,
    ) -> tuple[Optional[BaseIntent], bool]:
        """Return (intent_or_None, should_tick).

        Both values are independent: intent=None with should_tick=True advances
        a tick with a NoIntent (sapling growth etc. still occur).
        """
        ...

    @property
    def mode_name(self) -> str:
        return "unknown"


class ExternalIntentSource(IntentSource):
    """Thread-safe source for AI-driven intents.

    The AI thread calls ``submit(intent)``; the main thread calls
    ``poll_frame`` each frame and consumes one intent per call when available.
    """

    def __init__(self) -> None:
        self._queue: Queue[BaseIntent] = Queue()

    def submit(self, intent: BaseIntent) -> None:
        """Called from the AI thread to enqueue an intent."""
        self._queue.put(intent)

    def poll_frame(
        self,
        world: World,
        player_id: str,
        camera: pr.Camera3D,
        renderer: WorldRenderer,
    ) -> tuple[Optional[BaseIntent], bool]:
        try:
            return self._queue.get_nowait(), True
        except Empty:
            return None, False

    @property
    def mode_name(self) -> str:
        return "AI"


class HumanIntentSource(IntentSource):
    """Generates intents from keyboard and mouse input.

    Every distinct key press or mouse click triggers one intent + one tick,
    even when the resulting game action fails silently.
    """

    def poll_frame(
        self,
        world: World,
        player_id: str,
        camera: pr.Camera3D,
        renderer: WorldRenderer,
    ) -> tuple[Optional[BaseIntent], bool]:
        player = world.get_player(player_id)
        assert player is not None

        intent = self._keyboard_intent(player)
        if intent is not None:
            return intent, True

        intent = self._mouse_intent(world, player, camera, renderer)
        if intent is not None:
            return intent, True

        return None, False

    def _keyboard_intent(self, player: Player) -> Optional[BaseIntent]:
        # WASD → turn (absolute directions)
        if pr.is_key_pressed(pr.KEY_W):
            return TurnIntent(direction="north")
        if pr.is_key_pressed(pr.KEY_S):
            return TurnIntent(direction="south")
        if pr.is_key_pressed(pr.KEY_A):
            return TurnIntent(direction="west")
        if pr.is_key_pressed(pr.KEY_D):
            return TurnIntent(direction="east")

        # Space → walk forward
        if pr.is_key_pressed(pr.KEY_SPACE):
            return WalkIntent()

        # Z → wait one tick
        if pr.is_key_pressed(pr.KEY_Z):
            return NoIntent()

        # 1-9 → change active slot (slots are 0-indexed)
        for i in range(9):
            if pr.is_key_pressed(pr.KEY_ONE + i):
                return ChangeActiveSlotIntent(i)

        return None

    def _mouse_intent(
        self,
        world: World,
        player: Player,
        camera: pr.Camera3D,
        renderer: WorldRenderer,
    ) -> Optional[BaseIntent]:
        lmb = pr.is_mouse_button_pressed(pr.MOUSE_BUTTON_LEFT)
        rmb = pr.is_mouse_button_pressed(pr.MOUSE_BUTTON_RIGHT)

        if not lmb and not rmb:
            return None

        block_pos, face_normal = renderer.raycast_block(world, camera)

        if lmb:
            if block_pos is None or block_pos[1] < 0:
                # Clicked on ground (y=-1) or air → no-op dig
                return DigIntent()
            return DigIntent(target_position=Vec3I(*block_pos))

        # RMB → place block
        if block_pos is None:
            return None
        if face_normal is None:
            return None
        bx, by, bz = block_pos
        nx, ny, nz = face_normal
        place_pos = Vec3I(bx + nx, by + ny, bz + nz)

        item = player.main_hand_item
        if item is None:
            return None
        block_type = item.to_block_type()
        if block_type is None:
            return None

        return PlaceBlockIntent(block_type, place_pos)

    @property
    def mode_name(self) -> str:
        return "Human"
