from __future__ import annotations

import pytest

from minipy3dr import Material, ObjLoadError, load_obj, loads_obj
from minipy3dr.math import Vector3


def test_loads_obj_parses_vertices_and_triangulates_polygon() -> None:
    mesh = loads_obj(
        """
        # square as one quad
        v -1 0 0
        v 1 0 0
        v 1 1 0
        v -1 1 0
        f 1 2 3 4
        """
    )

    assert mesh.vertices == [
        Vector3(-1, 0, 0),
        Vector3(1, 0, 0),
        Vector3(1, 1, 0),
        Vector3(-1, 1, 0),
    ]
    assert mesh.faces == [(0, 1, 2), (0, 2, 3)]


def test_loads_obj_accepts_texture_normal_tokens_and_negative_indices() -> None:
    mesh = loads_obj(
        """
        v 0 0 0
        v 1 0 0
        v 0 1 0
        vt 0 0
        vn 0 0 1
        f -3/1/1 -2/1/1 -1/1/1
        """
    )

    assert mesh.faces == [(0, 1, 2)]


def test_load_obj_reads_file_and_assigns_material(tmp_path) -> None:
    obj_path = tmp_path / "triangle.obj"
    obj_path.write_text("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n", encoding="utf-8")
    material = Material(color=(20, 40, 60))

    mesh = load_obj(obj_path, material=material)

    assert mesh.material is material
    assert mesh.faces == [(0, 1, 2)]


def test_loads_obj_rejects_missing_faces() -> None:
    with pytest.raises(ObjLoadError, match="does not contain any faces"):
        loads_obj("v 0 0 0\nv 1 0 0\nv 0 1 0\n")


def test_loads_obj_rejects_out_of_range_face_index() -> None:
    with pytest.raises(ObjLoadError, match="out of range"):
        loads_obj("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 4\n")
