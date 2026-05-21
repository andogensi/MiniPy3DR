from __future__ import annotations

from minipy3dr import App, KeyboardCameraController, MiniPy3DRApp, Vector3, vec3


def test_high_level_api_exports_from_top_level_package() -> None:
    assert App is MiniPy3DRApp
    assert KeyboardCameraController is not None


def test_vec3_accepts_tuple_and_existing_vector() -> None:
    vector = Vector3(1, 2, 3)

    assert vec3((1, 2, 3)) == vector
    assert vec3(vector) is vector
