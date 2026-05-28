from __future__ import annotations

import math
import time
from array import array
from dataclasses import dataclass
from typing import List, Tuple, Optional

import moderngl
import moderngl_window as mglw

from game.core import BlockType
from game.world import World
from game.player import Player
from game.game import Game

import threading

Vec3 = Tuple[float, float, float]
Mat4 = List[float]


@dataclass
class RenderItem:
    position: Vec3
    scale: Vec3
    color: Vec3
    wireframe: bool = False


def _normalize(v: Vec3) -> Vec3:
    x, y, z = v
    length = math.sqrt(x * x + y * y + z * z)
    if length == 0:
        return (0.0, 0.0, 0.0)
    return (x / length, y / length, z / length)


def _mat4_identity() -> Mat4:
    return [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    ]


def _mat4_translate(tx: float, ty: float, tz: float) -> Mat4:
    return [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        tx, ty, tz, 1.0,
    ]


def _mat4_scale(sx: float, sy: float, sz: float) -> Mat4:
    return [
        sx, 0.0, 0.0, 0.0,
        0.0, sy, 0.0, 0.0,
        0.0, 0.0, sz, 0.0,
        0.0, 0.0, 0.0, 1.0,
    ]


def _mat4_mul(a: Mat4, b: Mat4) -> Mat4:
    result = [0.0] * 16
    for row in range(4):
        for col in range(4):
            result[row + col * 4] = sum(
                a[row + k * 4] * b[k + col * 4] for k in range(4)
            )
    return result


def _mat4_perspective(fovy_rad: float, aspect: float, near: float, far: float) -> Mat4:
    f = 1.0 / math.tan(fovy_rad / 2.0)
    nf = 1.0 / (near - far)
    return [
        f / aspect, 0.0, 0.0, 0.0,
        0.0, f, 0.0, 0.0,
        0.0, 0.0, (far + near) * nf, -1.0,
        0.0, 0.0, (2.0 * far * near) * nf, 0.0,
    ]


def _mat4_look_at(eye: Vec3, target: Vec3, up: Vec3) -> Mat4:
    ex, ey, ez = eye
    tx, ty, tz = target
    ux, uy, uz = up

    fx, fy, fz = _normalize((tx - ex, ty - ey, tz - ez))
    rx, ry, rz = _normalize((
        fy * uz - fz * uy,
        fz * ux - fx * uz,
        fx * uy - fy * ux,
    ))
    ux2, uy2, uz2 = (
        ry * fz - rz * fy,
        rz * fx - rx * fz,
        rx * fy - ry * fx,
    )

    return [
        rx, ux2, -fx, 0.0,
        ry, uy2, -fy, 0.0,
        rz, uz2, -fz, 0.0,
        -(rx * ex + ry * ey + rz * ez),
        -(ux2 * ex + uy2 * ey + uz2 * ez),
        fx * ex + fy * ey + fz * ez,
        1.0,
    ]


def _pack_mat4(mat: Mat4) -> bytes:
    return array("f", mat).tobytes()


def _build_cube_vertices() -> array:
    data = [
        # +X
        0.5, -0.5, -0.5, 1.0, 0.0, 0.0,
        0.5, 0.5, -0.5, 1.0, 0.0, 0.0,
        0.5, 0.5, 0.5, 1.0, 0.0, 0.0,
        0.5, -0.5, -0.5, 1.0, 0.0, 0.0,
        0.5, 0.5, 0.5, 1.0, 0.0, 0.0,
        0.5, -0.5, 0.5, 1.0, 0.0, 0.0,
        # -X
        -0.5, -0.5, -0.5, -1.0, 0.0, 0.0,
        -0.5, 0.5, 0.5, -1.0, 0.0, 0.0,
        -0.5, 0.5, -0.5, -1.0, 0.0, 0.0,
        -0.5, -0.5, -0.5, -1.0, 0.0, 0.0,
        -0.5, -0.5, 0.5, -1.0, 0.0, 0.0,
        -0.5, 0.5, 0.5, -1.0, 0.0, 0.0,
        # +Y
        -0.5, 0.5, -0.5, 0.0, 1.0, 0.0,
        -0.5, 0.5, 0.5, 0.0, 1.0, 0.0,
        0.5, 0.5, 0.5, 0.0, 1.0, 0.0,
        -0.5, 0.5, -0.5, 0.0, 1.0, 0.0,
        0.5, 0.5, 0.5, 0.0, 1.0, 0.0,
        0.5, 0.5, -0.5, 0.0, 1.0, 0.0,
        # -Y
        -0.5, -0.5, -0.5, 0.0, -1.0, 0.0,
        0.5, -0.5, 0.5, 0.0, -1.0, 0.0,
        -0.5, -0.5, 0.5, 0.0, -1.0, 0.0,
        -0.5, -0.5, -0.5, 0.0, -1.0, 0.0,
        0.5, -0.5, -0.5, 0.0, -1.0, 0.0,
        0.5, -0.5, 0.5, 0.0, -1.0, 0.0,
        # +Z
        -0.5, -0.5, 0.5, 0.0, 0.0, 1.0,
        0.5, -0.5, 0.5, 0.0, 0.0, 1.0,
        0.5, 0.5, 0.5, 0.0, 0.0, 1.0,
        -0.5, -0.5, 0.5, 0.0, 0.0, 1.0,
        0.5, 0.5, 0.5, 0.0, 0.0, 1.0,
        -0.5, 0.5, 0.5, 0.0, 0.0, 1.0,
        # -Z
        -0.5, -0.5, -0.5, 0.0, 0.0, -1.0,
        0.5, 0.5, -0.5, 0.0, 0.0, -1.0,
        0.5, -0.5, -0.5, 0.0, 0.0, -1.0,
        -0.5, -0.5, -0.5, 0.0, 0.0, -1.0,
        -0.5, 0.5, -0.5, 0.0, 0.0, -1.0,
        0.5, 0.5, -0.5, 0.0, 0.0, -1.0,
    ]
    return array("f", data)


def _build_cube_edges() -> array:
    edges = [
        (-0.5, -0.5, -0.5), (0.5, -0.5, -0.5),
        (0.5, -0.5, -0.5), (0.5, 0.5, -0.5),
        (0.5, 0.5, -0.5), (-0.5, 0.5, -0.5),
        (-0.5, 0.5, -0.5), (-0.5, -0.5, -0.5),
        (-0.5, -0.5, 0.5), (0.5, -0.5, 0.5),
        (0.5, -0.5, 0.5), (0.5, 0.5, 0.5),
        (0.5, 0.5, 0.5), (-0.5, 0.5, 0.5),
        (-0.5, 0.5, 0.5), (-0.5, -0.5, 0.5),
        (-0.5, -0.5, -0.5), (-0.5, -0.5, 0.5),
        (0.5, -0.5, -0.5), (0.5, -0.5, 0.5),
        (0.5, 0.5, -0.5), (0.5, 0.5, 0.5),
        (-0.5, 0.5, -0.5), (-0.5, 0.5, 0.5),
    ]
    data: List[float] = []
    for x, y, z in edges:
        data.extend([x, y, z])
    return array("f", data)


def _build_ground_vertices(size: float) -> array:
    half = size / 2.0
    z = -0.01
    data = [
        -half, -half, z, 0.0, 0.0, 1.0,
        half, -half, z, 0.0, 0.0, 1.0,
        half, half, z, 0.0, 0.0, 1.0,
        -half, -half, z, 0.0, 0.0, 1.0,
        half, half, z, 0.0, 0.0, 1.0,
        -half, half, z, 0.0, 0.0, 1.0,
    ]
    return array("f", data)


class WorldWindow(mglw.WindowConfig):
    gl_version = (3, 3)
    title = "Smart Bot World"
    window_size = (960, 720)
    target_fps = 10
    resource_dir = None

    world: Optional[World] = None
    player: Optional[Player] = None
    game: Optional[Game] = None
    world_lock: Optional[threading.Lock] = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if self.world_lock is None:
            self.world_lock = threading.Lock()
        self._auto_refresh = self.game is None

        self.ctx.enable(moderngl.DEPTH_TEST)

        self._start_time = time.time()
        self._tick_accumulator = 0.0
        self._last_tick_time = self._start_time

        self._cube_vbo = self.ctx.buffer(_build_cube_vertices())
        self._cube_edges_vbo = self.ctx.buffer(_build_cube_edges())

        ground_size = self._get_world_size()
        self._ground_vbo = self.ctx.buffer(_build_ground_vertices(ground_size))

        self._program = self.ctx.program(
            vertex_shader="""
                #version 330
                in vec3 in_position;
                in vec3 in_normal;
                uniform mat4 mvp;
                uniform mat4 model;
                out vec3 v_normal;
                out vec3 v_position;
                void main() {
                    v_normal = mat3(model) * in_normal;
                    v_position = (model * vec4(in_position, 1.0)).xyz;
                    gl_Position = mvp * vec4(in_position, 1.0);
                }
            """,
            fragment_shader="""
                #version 330
                in vec3 v_normal;
                in vec3 v_position;
                uniform vec3 color;
                uniform vec3 light_dir;
                uniform vec3 ambient_color;
                out vec4 f_color;
                void main() {
                    vec3 n = normalize(v_normal);
                    float diff = max(dot(n, normalize(-light_dir)), 0.0);
                    vec3 diffuse = color * diff;
                    vec3 ambient = color * ambient_color;
                    f_color = vec4(ambient + diffuse, 1.0);
                }
            """,
        )

        self._line_program = self.ctx.program(
            vertex_shader="""
                #version 330
                in vec3 in_position;
                uniform mat4 mvp;
                void main() {
                    gl_Position = mvp * vec4(in_position, 1.0);
                }
            """,
            fragment_shader="""
                #version 330
                uniform vec3 color;
                out vec4 f_color;
                void main() {
                    f_color = vec4(color, 1.0);
                }
            """,
        )

        self._cube_vao = self.ctx.vertex_array(
            self._program,
            [(self._cube_vbo, "3f 3f", "in_position", "in_normal")],
        )
        self._ground_vao = self.ctx.vertex_array(
            self._program,
            [(self._ground_vbo, "3f 3f", "in_position", "in_normal")],
        )
        self._edge_vao = self.ctx.vertex_array(
            self._line_program,
            [(self._cube_edges_vbo, "3f", "in_position")],
        )

        self._render_items: List[RenderItem] = []
        with self.world_lock:
            self._rebuild_scene()

    def _get_world_size(self) -> float:
        if self.world is None:
            return 6.0
        return float(self.world.game_state.world_size)

    def _camera_matrices(self) -> Tuple[Mat4, Mat4]:
        world_size = self._get_world_size()
        center = (world_size / 2.0 - 0.5, world_size / 2.0 - 0.5, 1.5)
        eye = (world_size * 1.6, -world_size * 1.2, world_size * 1.4)
        view = _mat4_look_at(eye, center, (0.0, 0.0, 1.0))
        proj = _mat4_perspective(math.radians(45.0), self.wnd.aspect_ratio, 0.1, 100.0)
        return view, proj

    def _rebuild_scene(self) -> None:
        self._render_items = []

        if self.world is None:
            return

        state = self.world.get_world_state()
        for block_info in state["blocks"]:
            bx, by, bz = block_info["position"]
            block_type = block_info["type"]
            position = (bx + 0.5, by + 0.5, bz + 0.5)
            scale = (1.0, 1.0, 1.0)

            if block_type == BlockType.PLANK.value:
                color = (0.55, 0.27, 0.07)
                self._render_items.append(RenderItem(position, scale, color, False))
            elif block_type == BlockType.LEAF.value:
                color = (0.2, 0.7, 0.2)
                self._render_items.append(RenderItem(position, scale, color, False))
            elif block_type == BlockType.SAPLING.value:
                color = (0.1, 0.8, 0.1)
                self._render_items.append(RenderItem(position, scale, color, True))

        if self.player is not None:
            px, py, pz = self.player.x, self.player.y, self.player.z
            position = (px + 0.5, py + 0.5, pz + 1.0)
            scale = (1.0, 1.0, 2.0)
            self._render_items.append(RenderItem(position, scale, (0.85, 0.1, 0.1), False))

            facing_dx, facing_dy, _ = self.player.direction.value
            thickness = 0.08
            offset = 0.5 + thickness / 2.0
            if abs(facing_dx) > 0:
                face_position = (px + 0.5 + facing_dx * offset, py + 0.5, pz + 1.0)
                face_scale = (thickness, 1.0, 2.0)
            else:
                face_position = (px + 0.5, py + 0.5 + facing_dy * offset, pz + 1.0)
                face_scale = (1.0, thickness, 2.0)
            self._render_items.append(RenderItem(face_position, face_scale, (0.1, 0.3, 0.9), False))

    def _draw_item(self, item: RenderItem, view: Mat4, proj: Mat4) -> None:
        model = _mat4_mul(_mat4_translate(*item.position), _mat4_scale(*item.scale))
        mvp = _mat4_mul(proj, _mat4_mul(view, model))

        if item.wireframe:
            self._line_program["mvp"].write(_pack_mat4(mvp))
            self._line_program["color"].value = item.color
            self._edge_vao.render(moderngl.LINES)
            return

        self._program["mvp"].write(_pack_mat4(mvp))
        self._program["model"].write(_pack_mat4(model))
        self._program["color"].value = item.color
        self._program["light_dir"].value = _normalize((1.0, -1.0, 2.0))
        self._program["ambient_color"].value = (0.25, 0.25, 0.25)
        self._cube_vao.render()

    def on_render(self, time: float, frame_time: float) -> None:
        self.ctx.clear(1.0, 1.0, 1.0)
        view, proj = self._camera_matrices()

        self._tick_accumulator += frame_time
        if self.game is not None and self._tick_accumulator >= 1.0:
            with self.world_lock:
                while self._tick_accumulator >= 1.0:
                    self.game.tick()
                    self._tick_accumulator -= 1.0
                self._rebuild_scene()
        elif self._auto_refresh:
            with self.world_lock:
                self._rebuild_scene()

        ground_model = _mat4_mul(_mat4_translate(self._get_world_size() / 2.0 - 0.5,
                                                self._get_world_size() / 2.0 - 0.5,
                                                0.0),
                                 _mat4_scale(self._get_world_size(),
                                             self._get_world_size(),
                                             1.0))
        ground_mvp = _mat4_mul(proj, _mat4_mul(view, ground_model))
        self._program["mvp"].write(_pack_mat4(ground_mvp))
        self._program["model"].write(_pack_mat4(ground_model))
        self._program["color"].value = (0.85, 0.85, 0.85)
        self._program["light_dir"].value = _normalize((1.0, -1.0, 2.0))
        self._program["ambient_color"].value = (0.3, 0.3, 0.3)
        self._ground_vao.render()

        with self.world_lock:
            for item in self._render_items:
                self._draw_item(item, view, proj)


def run_visualizer(
    world: World,
    player: Player,
    game: Optional[Game] = None,
    world_lock: Optional[threading.Lock] = None,
) -> None:
    WorldWindow.world = world
    WorldWindow.player = player
    WorldWindow.game = game
    WorldWindow.world_lock = world_lock or threading.Lock()
    mglw.run_window_config(WorldWindow)
