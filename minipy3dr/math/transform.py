"""Object transform helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
import math

from minipy3dr.math.matrix import Matrix4
from minipy3dr.math.vector import Vector3


@dataclass
class Transform:
    position: Vector3 = field(default_factory=Vector3)
    rotation: Vector3 = field(default_factory=Vector3)
    scale: Vector3 = field(default_factory=lambda: Vector3(1.0, 1.0, 1.0))

    def matrix(self) -> Matrix4:
        cx = math.cos(self.rotation.x)
        sx = math.sin(self.rotation.x)
        cy = math.cos(self.rotation.y)
        sy = math.sin(self.rotation.y)
        cz = math.cos(self.rotation.z)
        sz = math.sin(self.rotation.z)
        scale_x, scale_y, scale_z = self.scale.x, self.scale.y, self.scale.z

        return Matrix4._from_rows(
            (
                (
                    cz * cy * scale_x,
                    (cz * sy * sx - sz * cx) * scale_y,
                    (cz * sy * cx + sz * sx) * scale_z,
                    self.position.x,
                ),
                (
                    sz * cy * scale_x,
                    (sz * sy * sx + cz * cx) * scale_y,
                    (sz * sy * cx - cz * sx) * scale_z,
                    self.position.y,
                ),
                (
                    -sy * scale_x,
                    cy * sx * scale_y,
                    cy * cx * scale_z,
                    self.position.z,
                ),
                (0.0, 0.0, 0.0, 1.0),
            )
        )
