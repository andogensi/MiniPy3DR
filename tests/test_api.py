from __future__ import annotations

from types import SimpleNamespace

from minipy3dr import App, KeyboardCameraController, MiniPy3DRApp, Vector3, key_code_from_name, vec3


def test_high_level_api_exports_from_top_level_package() -> None:
    assert App is MiniPy3DRApp
    assert KeyboardCameraController is not None


def test_vec3_accepts_tuple_and_existing_vector() -> None:
    vector = Vector3(1, 2, 3)

    assert vec3((1, 2, 3)) == vector
    assert vec3(vector) is vector


def test_key_code_from_name_accepts_beginner_aliases() -> None:
    pygame = SimpleNamespace(K_LEFT=1, K_ESCAPE=2, K_SPACE=3)

    assert key_code_from_name(pygame, "left") == 1
    assert key_code_from_name(pygame, "esc") == 2
    assert key_code_from_name(pygame, "space") == 3
