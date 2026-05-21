"""Camera types."""

from __future__ import annotations

from dataclasses import dataclass

from minipy3dr.core.object3d import Object3D
from minipy3dr.math import Matrix4


@dataclass
class Camera(Object3D):
    def view_matrix(self) -> Matrix4:
        return (
            Matrix4.rotation_x(-self.rotation.x)
            @ Matrix4.rotation_y(-self.rotation.y)
            @ Matrix4.rotation_z(-self.rotation.z)
            @ Matrix4.translation(-self.position.x, -self.position.y, -self.position.z)
        )


@dataclass
class PerspectiveCamera(Camera):
    fov: float = 70.0
    aspect: float = 1.0
    near: float = 0.1
    far: float = 1000.0

    def projection_matrix(self) -> Matrix4:
        return Matrix4.perspective(self.fov, self.aspect, self.near, self.far)
