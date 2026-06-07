from __future__ import annotations

import math

import pyray as pr


class OrbitCamera:
    """Third-person orbit camera that rotates around a fixed target."""

    def __init__(
        self,
        target: tuple[float, float, float] = (2.0, 1.0, 2.0),
        distance: float = 14.0,
        yaw: float = -0.8,
        pitch: float = 0.55,
    ) -> None:
        self.target = pr.Vector3(*target)
        self.distance = distance
        self.yaw = yaw
        self.pitch = pitch
        self._min_dist = 3.0
        self._max_dist = 35.0
        self._min_pitch = 0.05
        self._max_pitch = 1.55

    def get_camera(self) -> pr.Camera3D:
        x = self.target.x + self.distance * math.cos(self.pitch) * math.sin(self.yaw)
        y = self.target.y + self.distance * math.sin(self.pitch)
        z = self.target.z + self.distance * math.cos(self.pitch) * math.cos(self.yaw)
        return pr.Camera3D(
            pr.Vector3(x, y, z),
            self.target,
            pr.Vector3(0.0, 1.0, 0.0),
            45.0,
            pr.CAMERA_PERSPECTIVE,
        )

    def update(self) -> None:
        if pr.is_mouse_button_down(pr.MOUSE_BUTTON_MIDDLE):
            delta = pr.get_mouse_delta()
            self.yaw += delta.x * 0.006
            self.pitch -= delta.y * 0.006
            self.pitch = max(self._min_pitch, min(self._max_pitch, self.pitch))

        wheel = pr.get_mouse_wheel_move()
        if wheel != 0:
            self.distance -= wheel * 0.8
            self.distance = max(self._min_dist, min(self._max_dist, self.distance))

        speed = pr.get_frame_time() * 4.0
        if pr.is_key_down(pr.KEY_RIGHT):
            self.target.x += speed
        if pr.is_key_down(pr.KEY_LEFT):
            self.target.x -= speed
        if pr.is_key_down(pr.KEY_UP):
            self.target.z -= speed
        if pr.is_key_down(pr.KEY_DOWN):
            self.target.z += speed
