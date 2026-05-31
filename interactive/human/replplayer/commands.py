"""Command parsing utilities for the REPL player."""
from __future__ import annotations

from game.core import BlockType, Direction, ItemType, Vec3I
from game.intent import (
    BaseIntent,
    CraftAxeIntent,
    DigIntent,
    NoIntent,
    PlaceBlockIntent,
    SwapInventoryIntent,
    TurnIntent,
    WalkIntent,
)
from game.player import Player

# Clockwise direction cycle (right-turn order)
_CW_DIRS = (Direction.EAST, Direction.SOUTH, Direction.WEST, Direction.NORTH)

# ItemType → BlockType reverse mapping (first BlockType that maps to each ItemType wins)
_ITEM_TO_BLOCK: dict[ItemType, BlockType] = {}
for _bt in BlockType:
    _it = _bt.to_item_type()
    _ITEM_TO_BLOCK.setdefault(_it, _bt)


HELP_TEXT = """\
Commands:
  status                  Show player position, facing, and inventory
  move                    Move forward one step
  turn back|left|right    Turn relative to current facing
  place high|low|down     Place main-hand block at target position
  dig   high|low|down     Dig block at target position
  swap <slot>             Swap main hand with inventory slot
  craft axe               Craft a wooden axe
  noop                    Advance one tick without acting
  help                    Show this help
  quit / exit             Exit the REPL"""


class ParseError(Exception):
    """Raised when a command line cannot be understood."""


def format_status(player: Player) -> str:
    lines = [
        f"Position: ({player.x}, {player.y}, {player.z})",
        f"Facing:   {player.direction.name.capitalize()}",
        "",
        "Main Hand:",
    ]
    main = player.main_hand_item
    lines.append(
        f"  {main.item_type.value.capitalize()} x{main.count}" if main else "  <Empty>"
    )
    lines += ["", "Inventory:"]
    for i, slot in enumerate(player.inventory):
        tag = " (main hand)" if i == player.main_hand_slot else ""
        if slot.item:
            name = slot.item.item_type.value.replace("_", " ").capitalize()
            lines.append(f"  [{i}] {name} x{slot.item.count}{tag}")
        else:
            lines.append(f"  [{i}] <Empty>{tag}")
    if player.breaking_block is not None:
        lines.append(
            f"\nBreaking: {tuple(player.breaking_block)}"
            f"  ({player.break_progress:.0f}/{player.break_target_time:.0f} ticks)"
        )
    return "\n".join(lines)


def _relative_to_direction(current: Direction, rel: str) -> Direction:
    idx = _CW_DIRS.index(current)
    if rel == "back":
        return _CW_DIRS[(idx + 2) % 4]
    if rel == "right":
        return _CW_DIRS[(idx - 1) % 4]
    if rel == "left":
        return _CW_DIRS[(idx + 1) % 4]
    raise ParseError(f"Unknown direction: {rel!r}. Use back, left, or right.")


def _place_target(player: Player, target: str) -> Vec3I:
    """Placement target: down = player's feet level (z=player.z)."""
    if target == "low":
        return player.get_facing_block_position()
    if target == "high":
        return player.get_facing_block_position_high()
    if target == "down":
        return player.get_place_down_position()
    raise ParseError(f"Unknown target: {target!r}. Use high, low, or down.")


def _dig_target(player: Player, target: str) -> Vec3I:
    """Dig target: down = one block below feet (z=player.z-1)."""
    if target == "low":
        return player.get_facing_block_position()
    if target == "high":
        return player.get_facing_block_position_high()
    if target == "down":
        return player.get_position_below()
    raise ParseError(f"Unknown target: {target!r}. Use high, low, or down.")


def parse_line(line: str, player: Player) -> BaseIntent | str:
    """Parse one command line.

    Returns:
      BaseIntent – game-advancing command; caller should submit + tick.
      "status"   – caller should print player status (no tick).
      "help"     – caller should print help text (no tick).
      "quit"     – caller should exit.
      ""         – blank line or comment; caller should skip.

    Raises ParseError on unrecognised or malformed input.
    """
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return ""

    parts = stripped.split()
    cmd = parts[0].lower()

    if cmd in ("quit", "exit"):
        return "quit"

    if cmd == "status":
        return "status"

    if cmd == "help":
        return "help"

    if cmd == "move":
        return WalkIntent()

    if cmd == "noop":
        return NoIntent()

    if cmd == "turn":
        if len(parts) < 2:
            raise ParseError("turn requires a direction: back, left, right")
        return TurnIntent(direction=_relative_to_direction(player.direction, parts[1].lower()))

    if cmd == "place":
        if len(parts) < 2:
            raise ParseError("place requires a target: high, low, down")
        pos = _place_target(player, parts[1].lower())
        main = player.main_hand_item
        if main is None:
            raise ParseError("Main hand is empty — nothing to place.")
        block_type = _ITEM_TO_BLOCK.get(main.item_type)
        if block_type is None:
            raise ParseError(f"{main.item_type.value!r} cannot be placed as a block.")
        return PlaceBlockIntent(block_type, pos)

    if cmd == "dig":
        if len(parts) < 2:
            raise ParseError("dig requires a target: high, low, down")
        pos = _dig_target(player, parts[1].lower())
        return DigIntent(target_position=pos)

    if cmd == "swap":
        if len(parts) < 2:
            raise ParseError("swap requires a slot number")
        try:
            slot = int(parts[1])
        except ValueError:
            raise ParseError(f"Invalid slot number: {parts[1]!r}")
        return SwapInventoryIntent(slot1=0, slot2=slot)

    if cmd == "craft":
        if len(parts) < 2 or parts[1].lower() != "axe":
            raise ParseError("craft requires: craft axe")
        return CraftAxeIntent()

    raise ParseError(f"Unknown command: {cmd!r}. Type 'help' for available commands.")
