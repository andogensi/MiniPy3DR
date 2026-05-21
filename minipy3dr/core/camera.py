"""Camera types."""

from __future__ import annotations

from dataclasses import dataclass
import math

from minipy3dr.core.object3d import Object3D
from minipy3dr.math import Matrix4, Vector3


@dataclass
class Camera(Object3D):
    def view_matrix(self) -> Matrix4:
        return (
            Matrix4.rotation_x(-self.rotation.x)
            @ Matrix4.rotation_y(-self.rotation.y)
            @ Matrix4.rotation_z(-self.rotation.z)
            @ Matrix4.translation(-self.position.x, -self.position.y, -self.position.z)
        )

    @property
    def forward(self) -> Vector3:
        return Matrix4.euler_xyz(self.rotation).transform_direction(Vector3(0, 0, -1)).normalized()

    @property
    def right(self) -> Vector3:
        return Matrix4.euler_xyz(self.rotation).transform_direction(Vector3(1, 0, 0)).normalized()

    @property
    def up(self) -> Vector3:
        return Matrix4.euler_xyz(self.rotation).transform_direction(Vector3(0, 1, 0)).normalized()

    def move(self, offset: Vector3) -> Camera:
        self.position = self.position + offset
        return self

    def move_local(self, right: float = 0.0, up: float = 0.0, forward: float = 0.0) -> Camera:
        return self.move(self.right * right + self.up * up + self.forward * forward)

    def rotate(self, pitch: float = 0.0, yaw: float = 0.0, roll: float = 0.0) -> Camera:
        self.rotation = Vector3(
            self.rotation.x + pitch,
            self.rotation.y + yaw,
            self.rotation.z + roll,
        )
        return self

    def look_at(self, target: Vector3) -> Camera:
        direction = target - self.position
        length = direction.length()
        if length == 0:
            raise ValueError("Camera cannot look at its own position")

        normalized = direction / length
        pitch = math.asin(max(-1.0, min(1.0, normalized.y)))
        yaw = math.atan2(-normalized.x, -normalized.z)
        self.rotation = Vector3(pitch, yaw, 0.0)
        return self


@dataclass
class PerspectiveCamera(Camera):
    fov: float = 70.0
    aspect: float = 1.0
    near: float = 0.1
    far: float = 1000.0

    def projection_matrix(self) -> Matrix4:
        return Matrix4.perspective(self.fov, self.aspect, self.near, self.far)
