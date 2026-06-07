from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pyray as pr


@dataclass
class InputSnapshot:
    """Records all relevant inputs for a single frame."""

    # Keyboard: direction turn (W/A/S/D)
    turn_direction: Optional[str] = None   # "north" | "south" | "east" | "west"

    # Walk (Space)
    walk: bool = False

    # Wait (Z)
    wait: bool = False

    # Hotbar slot 0-8 (keys 1-9)
    slot_select: Optional[int] = None

    # Mouse clicks (pressed this frame only)
    lmb_pressed: bool = False
    rmb_pressed: bool = False

    # Mouse position
    mouse_x: float = 0.0
    mouse_y: float = 0.0


def poll_input() -> InputSnapshot:
    """Snapshot all relevant inputs for the current frame."""
    snap = InputSnapshot()

    # WASD → turn directions (absolute)
    if pr.is_key_pressed(pr.KEY_W):
        snap.turn_direction = "north"
    elif pr.is_key_pressed(pr.KEY_S):
        snap.turn_direction = "south"
    elif pr.is_key_pressed(pr.KEY_A):
        snap.turn_direction = "west"
    elif pr.is_key_pressed(pr.KEY_D):
        snap.turn_direction = "east"

    if pr.is_key_pressed(pr.KEY_SPACE):
        snap.walk = True

    if pr.is_key_pressed(pr.KEY_Z):
        snap.wait = True

    # Number keys 1-9 → hotbar slots 0-8
    for i in range(9):
        if pr.is_key_pressed(pr.KEY_ONE + i):
            snap.slot_select = i
            break

    snap.lmb_pressed = pr.is_mouse_button_pressed(pr.MOUSE_BUTTON_LEFT)
    snap.rmb_pressed = pr.is_mouse_button_pressed(pr.MOUSE_BUTTON_RIGHT)

    mouse = pr.get_mouse_position()
    snap.mouse_x = mouse.x
    snap.mouse_y = mouse.y

    return snap
