"""Mesh primitives."""

from __future__ import annotations

from dataclasses import dataclass, field

from minipy3dr.core.material import Material
from minipy3dr.core.object3d import Object3D
from minipy3dr.math import Vector3


Face = tuple[int, int, int]
Edge = tuple[int, int]


@dataclass
class Mesh(Object3D):
    vertices: list[Vector3] = field(default_factory=list)
    faces: list[Face] = field(default_factory=list)
    wire_edges: list[Edge] = field(default_factory=list)
    material: Material | None = None

    @staticmethod
    def cube(size: float = 1.0) -> Mesh:
        half = size / 2.0
        vertices = [
            Vector3(-half, -half, -half),
            Vector3(half, -half, -half),
            Vector3(half, half, -half),
            Vector3(-half, half, -half),
            Vector3(-half, -half, half),
            Vector3(half, -half, half),
            Vector3(half, half, half),
            Vector3(-half, half, half),
        ]
        faces = [
            (0, 2, 1),
            (0, 3, 2),
            (4, 5, 6),
            (4, 6, 7),
            (0, 4, 7),
            (0, 7, 3),
            (1, 2, 6),
            (1, 6, 5),
            (3, 7, 6),
            (3, 6, 2),
            (0, 1, 5),
            (0, 5, 4),
        ]
        wire_edges = [
            (0, 1),
            (1, 2),
            (2, 3),
            (3, 0),
            (4, 5),
            (5, 6),
            (6, 7),
            (7, 4),
            (0, 4),
            (1, 5),
            (2, 6),
            (3, 7),
        ]
        return Mesh(vertices=vertices, faces=faces, wire_edges=wire_edges)

    def edges(self) -> list[Edge]:
        if self.wire_edges:
            return list(self.wire_edges)

        seen: set[Edge] = set()
        result: list[Edge] = []
        for a, b, c in self.faces:
            for edge in ((a, b), (b, c), (c, a)):
                normalized = tuple(sorted(edge))
                if normalized not in seen:
                    seen.add(normalized)
                    result.append(edge)
        return result
