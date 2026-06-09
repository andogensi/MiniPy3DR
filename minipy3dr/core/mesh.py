"""Mesh primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
import math

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

    @staticmethod
    def sphere(radius: float = 1.0, segments: int = 16, rings: int = 8) -> Mesh:
        """Create a UV sphere mesh."""
        if radius <= 0:
            raise ValueError("radius must be greater than 0")
        if segments < 3:
            raise ValueError("segments must be at least 3")
        if rings < 2:
            raise ValueError("rings must be at least 2")

        vertices = [Vector3(0.0, radius, 0.0)]
        for ring in range(1, rings):
            phi = math.pi * ring / rings
            y = math.cos(phi) * radius
            ring_radius = math.sin(phi) * radius
            for segment in range(segments):
                theta = 2.0 * math.pi * segment / segments
                vertices.append(
                    Vector3(
                        math.cos(theta) * ring_radius,
                        y,
                        math.sin(theta) * ring_radius,
                    )
                )
        bottom_index = len(vertices)
        vertices.append(Vector3(0.0, -radius, 0.0))

        faces: list[Face] = []
        for segment in range(segments):
            next_segment = (segment + 1) % segments
            faces.append((0, 1 + next_segment, 1 + segment))

        for ring in range(rings - 2):
            current = 1 + ring * segments
            next_ring = current + segments
            for segment in range(segments):
                next_segment = (segment + 1) % segments
                a = current + segment
                b = current + next_segment
                c = next_ring + segment
                d = next_ring + next_segment
                faces.append((a, b, d))
                faces.append((a, d, c))

        last_ring = 1 + (rings - 2) * segments
        for segment in range(segments):
            next_segment = (segment + 1) % segments
            faces.append((bottom_index, last_ring + segment, last_ring + next_segment))

        wire_edges: list[Edge] = []
        for segment in range(segments):
            next_segment = (segment + 1) % segments
            wire_edges.append((0, 1 + segment))
            wire_edges.append((last_ring + segment, bottom_index))
            for ring in range(rings - 1):
                current = 1 + ring * segments + segment
                current_next = 1 + ring * segments + next_segment
                wire_edges.append((current, current_next))
                if ring < rings - 2:
                    wire_edges.append((current, current + segments))

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
