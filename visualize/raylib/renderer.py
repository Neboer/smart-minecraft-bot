from __future__ import annotations

import os
from typing import Optional, TYPE_CHECKING

import pyray as pr

from game.core import BlockType

if TYPE_CHECKING:
    from game.world import World
    from game.player import Player

_ASSETS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets"))

_SKYBOX_VS = """
#version 330
in vec3 vertexPosition;
uniform mat4 matProjection;
uniform mat4 matView;
out vec3 fragTexCoord;
void main() {
    fragTexCoord = vertexPosition;
    mat4 rotView = mat4(mat3(matView));
    vec4 clipPos = matProjection * rotView * vec4(vertexPosition, 1.0);
    gl_Position = clipPos.xyww;
}
"""

_SKYBOX_FS = """
#version 330
in vec3 fragTexCoord;
uniform samplerCube environmentMap;
out vec4 finalColor;
void main() {
    finalColor = texture(environmentMap, fragTexCoord);
}
"""

_WORLD_SIZE = 5


def _asset(relative: str) -> str:
    return os.path.join(_ASSETS, relative)


def _make_block_model(texture: pr.Texture2D) -> pr.Model:
    mesh = pr.gen_mesh_cube(1.0, 1.0, 1.0)
    model = pr.load_model_from_mesh(mesh)
    model.materials[0].maps[pr.MATERIAL_MAP_ALBEDO].texture = texture
    return model


class WorldRenderer:
    """Renders the game world using Raylib 3D drawing primitives."""

    def __init__(self) -> None:
        self._ready = False
        self._skybox_ready = False

    def load(self) -> None:
        self._tex_plank = pr.load_texture(_asset("textures/block/oak_log.png"))
        self._tex_leaf = pr.load_texture(_asset("textures/block/oak_leaves_colored.png"))
        self._tex_sapling = pr.load_texture(_asset("textures/block/oak_sapling.png"))
        self._tex_ground = pr.load_texture(_asset("textures/block/grass_block_top_colored.png"))

        pr.set_texture_filter(self._tex_plank, pr.TEXTURE_FILTER_POINT)
        pr.set_texture_filter(self._tex_leaf, pr.TEXTURE_FILTER_POINT)
        pr.set_texture_filter(self._tex_sapling, pr.TEXTURE_FILTER_POINT)
        pr.set_texture_filter(self._tex_ground, pr.TEXTURE_FILTER_POINT)

        self._model_plank = _make_block_model(self._tex_plank)
        self._model_leaf = _make_block_model(self._tex_leaf)
        self._model_ground = _make_block_model(self._tex_ground)

        self._init_skybox()
        self._ready = True

    def _init_skybox(self) -> None:
        try:
            skybox_path = _asset("textures/skybox/Daylight Box UV.png")
            img = pr.load_image(skybox_path)
            cubemap = pr.load_texture_cubemap(img, pr.CUBEMAP_LAYOUT_CROSS_FOUR_BY_THREE)
            pr.unload_image(img)

            shader = pr.load_shader_from_memory(_SKYBOX_VS, _SKYBOX_FS)

            # Tell raylib which shader locs to auto-update with camera matrices
            shader.locs[pr.SHADER_LOC_MATRIX_VIEW] = pr.get_shader_location(shader, "matView")
            shader.locs[pr.SHADER_LOC_MATRIX_PROJECTION] = pr.get_shader_location(shader, "matProjection")

            env_loc = pr.get_shader_location(shader, "environmentMap")
            env_val = pr.ffi.new("int []", [pr.MATERIAL_MAP_CUBEMAP])
            pr.set_shader_value(shader, env_loc, env_val, pr.SHADER_UNIFORM_INT)

            mesh = pr.gen_mesh_cube(1.0, 1.0, 1.0)
            self._skybox_model = pr.load_model_from_mesh(mesh)
            self._skybox_model.materials[0].shader = shader
            self._skybox_model.materials[0].maps[pr.MATERIAL_MAP_CUBEMAP].texture = cubemap
            self._skybox_ready = True
        except Exception as exc:
            print(f"[renderer] skybox init failed: {exc}")
            self._skybox_ready = False

    def unload(self) -> None:
        if not self._ready:
            return
        pr.unload_texture(self._tex_plank)
        pr.unload_texture(self._tex_leaf)
        pr.unload_texture(self._tex_sapling)
        pr.unload_texture(self._tex_ground)
        pr.unload_model(self._model_plank)
        pr.unload_model(self._model_leaf)
        pr.unload_model(self._model_ground)
        if self._skybox_ready:
            pr.unload_model(self._skybox_model)

    # ── Public draw entry point ──────────────────────────────────────────────

    def draw(
        self,
        world: World,
        player: Optional[Player],
        camera: pr.Camera3D,
    ) -> None:
        """Draw the full 3D scene. Must be called inside BeginMode3D/EndMode3D."""
        if not self._ready:
            return

        self._draw_skybox(camera)
        self._draw_ground()
        self._draw_blocks(world, player)
        if player is not None:
            self._draw_player(player, camera)

    # ── Skybox ───────────────────────────────────────────────────────────────

    def _draw_skybox(self, camera: pr.Camera3D) -> None:
        if not self._skybox_ready:
            return
        try:
            pr.rl_disable_backface_culling()
            pr.rl_disable_depth_mask()
            pr.draw_model(
                self._skybox_model,
                pr.Vector3(camera.position.x, camera.position.y, camera.position.z),
                1.0,
                pr.WHITE,
            )
            pr.rl_enable_backface_culling()
            pr.rl_enable_depth_mask()
        except Exception:
            self._skybox_ready = False

    # ── Ground ───────────────────────────────────────────────────────────────

    def _draw_ground(self) -> None:
        for gx in range(_WORLD_SIZE):
            for gz in range(_WORLD_SIZE):
                pr.draw_model(
                    self._model_ground,
                    pr.Vector3(gx + 0.5, -0.5, gz + 0.5),
                    1.0,
                    pr.WHITE,
                )

    # ── World blocks ─────────────────────────────────────────────────────────

    def _draw_blocks(self, world: World, player: Optional[Player]) -> None:
        breaking_pos: Optional[tuple[int, int, int]] = None
        if player is not None and player.breaking_block is not None:
            breaking_pos = tuple(player.breaking_block)

        # Collect saplings separately (transparent/billboard)
        sapling_positions: list[tuple[int, int, int]] = []

        for (bx, by, bz), block in world.game_state.blocks.items():
            cx = bx + 0.5
            cy = by + 0.5
            cz = bz + 0.5

            if block.block_type == BlockType.SAPLING:
                sapling_positions.append((bx, by, bz))
                continue

            if block.block_type == BlockType.PLANK:
                pr.draw_model(self._model_plank, pr.Vector3(cx, cy, cz), 1.0, pr.WHITE)
            elif block.block_type == BlockType.LEAF:
                pr.draw_model(self._model_leaf, pr.Vector3(cx, cy, cz), 1.0, pr.Color(255, 255, 255, 200))

            if (bx, by, bz) == breaking_pos:
                self._draw_break_highlight(bx, by, bz, player)

        # Draw saplings as billboards (after opaque blocks)
        for bx, by, bz in sapling_positions:
            pr.draw_billboard(
                _current_camera(),
                self._tex_sapling,
                pr.Vector3(bx + 0.5, by + 0.5, bz + 0.5),
                1.0,
                pr.WHITE,
            )

    def _draw_break_highlight(self, bx: int, by: int, bz: int, player: Player) -> None:
        target_time = player.break_target_time
        if target_time > 0:
            progress = player.break_progress / target_time
        else:
            progress = 1.0
        # Black wireframe, slightly larger than block; gets thicker with progress
        thickness = 0.01 + progress * 0.04
        size = 1.0 + thickness * 2
        pr.draw_cube_wires(
            pr.Vector3(bx + 0.5, by + 0.5, bz + 0.5),
            size, size, size,
            pr.BLACK,
        )

    # ── Player ───────────────────────────────────────────────────────────────

    def _draw_player(self, player: Player, camera: pr.Camera3D) -> None:
        px, py, pz = player.x, player.y, player.z
        # Wireframe box: width=1, height=2, length=1
        pr.draw_cube_wires(
            pr.Vector3(px + 0.5, py + 1.0, pz + 0.5),
            1.0, 2.0, 1.0,
            pr.GREEN,
        )
        # Facing direction arrow
        dx, _, dz = player.direction.value
        cx, cy, cz = px + 0.5, py + 1.0, pz + 0.5
        pr.draw_line_3d(
            pr.Vector3(cx, cy, cz),
            pr.Vector3(cx + dx * 0.8, cy, cz + dz * 0.8),
            pr.BLUE,
        )

    # ── Ray casting ─────────────────────────────────────────────────────────

    def raycast_block(
        self, world: World, camera: pr.Camera3D
    ) -> tuple[Optional[tuple[int, int, int]], Optional[tuple[int, int, int]]]:
        """Return (block_pos, face_normal) for the block under the mouse cursor."""
        mouse = pr.get_mouse_position()
        ray = pr.get_screen_to_world_ray(mouse, camera)

        best_dist = float("inf")
        best_pos: Optional[tuple[int, int, int]] = None
        best_normal: Optional[tuple[int, int, int]] = None

        for pos in world.game_state.blocks:
            bx, by, bz = pos
            box = pr.BoundingBox(pr.Vector3(bx, by, bz), pr.Vector3(bx + 1, by + 1, bz + 1))
            coll = pr.get_ray_collision_box(ray, box)
            if coll.hit and coll.distance < best_dist:
                best_dist = coll.distance
                best_pos = pos
                best_normal = (
                    round(coll.normal.x),
                    round(coll.normal.y),
                    round(coll.normal.z),
                )

        # Also check ground blocks at y=-1
        for gx in range(_WORLD_SIZE):
            for gz in range(_WORLD_SIZE):
                box = pr.BoundingBox(pr.Vector3(gx, -1, gz), pr.Vector3(gx + 1, 0, gz + 1))
                coll = pr.get_ray_collision_box(ray, box)
                if coll.hit and coll.distance < best_dist:
                    best_dist = coll.distance
                    best_pos = (gx, -1, gz)
                    best_normal = (
                        round(coll.normal.x),
                        round(coll.normal.y),
                        round(coll.normal.z),
                    )

        return best_pos, best_normal


# Module-level camera reference so _draw_blocks can pass camera to billboard.
_camera_ref: Optional[pr.Camera3D] = None


def set_current_camera(camera: pr.Camera3D) -> None:
    global _camera_ref
    _camera_ref = camera


def _current_camera() -> pr.Camera3D:
    return _camera_ref  # type: ignore[return-value]
