"""Base transformable scene object."""

from __future__ import annotations

from dataclasses import dataclass, field

from minipy3dr.math import Matrix4, Transform, Vector3


@dataclass
class Object3D:
    position: Vector3 = field(default_factory=Vector3)
    rotation: Vector3 = field(default_factory=Vector3)
    scale: Vector3 = field(default_factory=lambda: Vector3(1.0, 1.0, 1.0))
    visible: bool = True

    @property
    def transform(self) -> Transform:
        return Transform(self.position, self.rotation, self.scale)

    def local_matrix(self) -> Matrix4:
        return self.transform.matrix()
