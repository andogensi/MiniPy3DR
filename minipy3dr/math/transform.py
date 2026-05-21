"""Object transform helpers."""

from __future__ import annotations

from dataclasses import dataclass, field

from minipy3dr.math.matrix import Matrix4
from minipy3dr.math.vector import Vector3


@dataclass
class Transform:
    position: Vector3 = field(default_factory=Vector3)
    rotation: Vector3 = field(default_factory=Vector3)
    scale: Vector3 = field(default_factory=lambda: Vector3(1.0, 1.0, 1.0))

    def matrix(self) -> Matrix4:
        return (
            Matrix4.translation(self.position.x, self.position.y, self.position.z)
            @ Matrix4.euler_xyz(self.rotation)
            @ Matrix4.scale(self.scale.x, self.scale.y, self.scale.z)
        )
