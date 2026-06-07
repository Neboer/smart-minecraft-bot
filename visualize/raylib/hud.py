from __future__ import annotations

import os
from typing import Optional, TYPE_CHECKING

import pyray as pr

from game.core import ItemType

if TYPE_CHECKING:
    from game.player import Player
    from game.game import Game

_ASSETS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets"))

_SLOT_SIZE = 44
_SLOT_PAD = 4
_SLOT_COUNT = 9

# Item icon texture paths keyed by ItemType
_ITEM_TEX_PATHS = {
    ItemType.SAPLING: os.path.join(_ASSETS, "textures/block/oak_sapling.png"),
    ItemType.PLANK: os.path.join(_ASSETS, "textures/block/oak_log.png"),
    ItemType.WOODEN_AXE: os.path.join(_ASSETS, "textures/item/wooden_axe.png"),
}


class HUD:
    """2D overlay: inventory bar, player info, dig progress, debug info."""

    def __init__(self) -> None:
        self._ready = False

    def load(self) -> None:
        self._item_textures: dict[ItemType, pr.Texture2D] = {}
        for item_type, path in _ITEM_TEX_PATHS.items():
            if os.path.exists(path):
                tex = pr.load_texture(path)
                pr.set_texture_filter(tex, pr.TEXTURE_FILTER_POINT)
                self._item_textures[item_type] = tex
        self._ready = True

    def unload(self) -> None:
        for tex in self._item_textures.values():
            pr.unload_texture(tex)

    def draw(
        self,
        player: Optional[Player],
        game: Game,
        mode_name: str,
    ) -> None:
        if not self._ready or player is None:
            return

        sw = pr.get_screen_width()
        sh = pr.get_screen_height()

        self._draw_inventory(player, sw, sh)
        self._draw_info(player, game, mode_name, sw)
        self._draw_dig_info(player, sw)

    # ── Inventory bar ────────────────────────────────────────────────────────

    def _draw_inventory(self, player: Player, sw: int, sh: int) -> None:
        total_w = _SLOT_COUNT * (_SLOT_SIZE + _SLOT_PAD) - _SLOT_PAD
        bar_x = (sw - total_w) // 2
        bar_y = sh - _SLOT_SIZE - 12

        for i, slot in enumerate(player.inventory):
            sx = bar_x + i * (_SLOT_SIZE + _SLOT_PAD)
            sy = bar_y

            # Background
            is_active = i == player.main_hand_slot
            bg_color = pr.Color(40, 40, 40, 200) if not is_active else pr.Color(255, 255, 255, 220)
            border_color = pr.Color(255, 215, 0, 255) if is_active else pr.Color(100, 100, 100, 200)

            pr.draw_rectangle(sx, sy, _SLOT_SIZE, _SLOT_SIZE, bg_color)
            pr.draw_rectangle_lines(sx, sy, _SLOT_SIZE, _SLOT_SIZE, border_color)

            if slot.item is not None and slot.item.count > 0:
                item_type = slot.item.item_type
                tex = self._item_textures.get(item_type)
                if tex is not None:
                    src = pr.Rectangle(0, 0, tex.width, tex.height)
                    dst = pr.Rectangle(sx + 4, sy + 4, _SLOT_SIZE - 8, _SLOT_SIZE - 8)
                    pr.draw_texture_pro(tex, src, dst, pr.Vector2(0, 0), 0.0, pr.WHITE)

                if slot.item.count > 1:
                    count_text = str(slot.item.count)
                    cw = pr.measure_text(count_text, 10)
                    pr.draw_text(count_text, sx + _SLOT_SIZE - cw - 3, sy + _SLOT_SIZE - 13, 10, pr.WHITE)

    # ── Player info (top-left) ───────────────────────────────────────────────

    def _draw_info(self, player: Player, game: Game, mode_name: str, sw: int) -> None:
        lines = [
            f"Mode: {mode_name}",
            f"Tick: {game.world.game_state.tick_count}",
            f"Pos: ({player.x}, {player.y}, {player.z})",
            f"Dir: {player.direction.name.lower()}",
        ]
        # Main hand item
        item = player.main_hand_item
        if item is not None:
            lines.append(f"Hand: {item.item_type.value} x{item.count}")
        else:
            lines.append("Hand: (empty)")

        y = 10
        for line in lines:
            pr.draw_text(line, 10, y, 16, pr.WHITE)
            # subtle shadow
            pr.draw_text(line, 11, y + 1, 16, pr.Color(0, 0, 0, 160))
            pr.draw_text(line, 10, y, 16, pr.WHITE)
            y += 20

        # FPS top-right
        fps_text = f"FPS: {pr.get_fps()}"
        fw = pr.measure_text(fps_text, 16)
        pr.draw_text(fps_text, sw - fw - 10, 10, 16, pr.LIME)

    # ── Dig progress ─────────────────────────────────────────────────────────

    def _draw_dig_info(self, player: Player, sw: int) -> None:
        if player.breaking_block is None:
            return

        bx, by, bz = player.breaking_block
        target_time = player.break_target_time
        progress = player.break_progress / target_time if target_time > 0 else 1.0

        lines = [
            f"Breaking: ({bx}, {by}, {bz})",
            f"Progress: {progress * 100:.0f}%",
        ]

        y = 10
        for line in lines:
            tw = pr.measure_text(line, 16)
            pr.draw_text(line, sw // 2 - tw // 2, y, 16, pr.ORANGE)
            y += 20

        # Progress bar
        bar_w = 200
        bar_h = 10
        bx_screen = sw // 2 - bar_w // 2
        by_screen = y + 2
        pr.draw_rectangle(bx_screen, by_screen, bar_w, bar_h, pr.Color(80, 80, 80, 200))
        pr.draw_rectangle(bx_screen, by_screen, int(bar_w * progress), bar_h, pr.ORANGE)
        pr.draw_rectangle_lines(bx_screen, by_screen, bar_w, bar_h, pr.WHITE)
