"""Wavefront OBJ mesh loader."""

from __future__ import annotations

from collections.abc import Iterable
from os import PathLike

from minipy3dr.core import Material, Mesh
from minipy3dr.math import Vector3


class ObjLoadError(ValueError):
    """Raised when OBJ mesh data cannot be parsed."""


def load_obj(path: str | PathLike[str], material: Material | None = None) -> Mesh:
    """Load a Wavefront OBJ file into a :class:`~minipy3dr.core.Mesh`.

    The current renderer consumes positions and triangle faces, so texture
    coordinates, normals, groups, and material library records are ignored.
    Polygonal faces are triangulated with a simple fan.
    """

    with open(path, encoding="utf-8") as file:
        return loads_obj(file, material=material)


def loads_obj(source: str | Iterable[str], material: Material | None = None) -> Mesh:
    """Parse Wavefront OBJ text into a :class:`~minipy3dr.core.Mesh`."""

    lines = source.splitlines() if isinstance(source, str) else source
    vertices: list[Vector3] = []
    faces: list[tuple[int, int, int]] = []

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue

        parts = line.split()
        command = parts[0]
        values = parts[1:]

        if command == "v":
            vertices.append(_parse_vertex(values, line_number))
        elif command == "f":
            face_indices = _parse_face(values, len(vertices), line_number)
            faces.extend(_triangulate(face_indices))

    if not vertices:
        raise ObjLoadError("OBJ data does not contain any vertices")
    if not faces:
        raise ObjLoadError("OBJ data does not contain any faces")

    return Mesh(vertices=vertices, faces=faces, material=material)


def _parse_vertex(values: list[str], line_number: int) -> Vector3:
    if len(values) < 3:
        raise ObjLoadError(f"Line {line_number}: vertex requires at least 3 coordinates")
    try:
        return Vector3(float(values[0]), float(values[1]), float(values[2]))
    except ValueError as exc:
        raise ObjLoadError(f"Line {line_number}: invalid vertex coordinate") from exc


def _parse_face(values: list[str], vertex_count: int, line_number: int) -> list[int]:
    if len(values) < 3:
        raise ObjLoadError(f"Line {line_number}: face requires at least 3 vertices")

    indices: list[int] = []
    for token in values:
        vertex_token = token.split("/", 1)[0]
        if not vertex_token:
            raise ObjLoadError(f"Line {line_number}: face vertex is missing a position index")
        try:
            obj_index = int(vertex_token)
        except ValueError as exc:
            raise ObjLoadError(f"Line {line_number}: invalid face vertex index") from exc

        index = _resolve_obj_index(obj_index, vertex_count, line_number)
        indices.append(index)

    return indices


def _resolve_obj_index(obj_index: int, vertex_count: int, line_number: int) -> int:
    if obj_index > 0:
        index = obj_index - 1
    elif obj_index < 0:
        index = vertex_count + obj_index
    else:
        raise ObjLoadError(f"Line {line_number}: OBJ indices are 1-based")

    if index < 0 or index >= vertex_count:
        raise ObjLoadError(f"Line {line_number}: face vertex index is out of range")
    return index


def _triangulate(indices: list[int]) -> list[tuple[int, int, int]]:
    first = indices[0]
    return [(first, indices[index], indices[index + 1]) for index in range(1, len(indices) - 1)]


__all__ = ["ObjLoadError", "load_obj", "loads_obj"]
