from __future__ import annotations

import math

from minipy3dr import PerspectiveCamera
from minipy3dr.math import Matrix4, Transform, Vector3, Vector4


def test_vector_cross_product() -> None:
    assert Vector3(1, 0, 0).cross(Vector3(0, 1, 0)) == Vector3(0, 0, 1)


def test_matrix_translation_transforms_point() -> None:
    matrix = Matrix4.translation(2, 3, -4)

    assert matrix.transform_point(Vector3(1, 1, 1)) == Vector3(3, 4, -3)


def test_transform_matrix_matches_composed_matrix() -> None:
    transform = Transform(
        position=Vector3(2, -1, -4),
        rotation=Vector3(0.3, -0.4, 0.8),
        scale=Vector3(1.5, 0.75, 2.0),
    )
    composed = (
        Matrix4.translation(transform.position.x, transform.position.y, transform.position.z)
        @ Matrix4.euler_xyz(transform.rotation)
        @ Matrix4.scale(transform.scale.x, transform.scale.y, transform.scale.z)
    )

    for actual_row, expected_row in zip(transform.matrix().rows, composed.rows):
        for actual, expected in zip(actual_row, expected_row):
            assert math.isclose(actual, expected)


def test_perspective_projects_camera_forward_point() -> None:
    projection = Matrix4.perspective(90, 1, 0.1, 100)
    clip = projection @ Vector4(0, 0, -1, 1)

    assert math.isclose(clip.x / clip.w, 0.0)
    assert math.isclose(clip.y / clip.w, 0.0)


def test_camera_move_local_uses_camera_axes() -> None:
    camera = PerspectiveCamera()

    camera.move_local(right=1.5, up=0.5, forward=2.0)

    assert camera.position == Vector3(1.5, 0.5, -2.0)


def test_camera_look_at_updates_forward_direction() -> None:
    camera = PerspectiveCamera()

    camera.look_at(Vector3(-1, 0, 0))

    assert math.isclose(camera.forward.x, -1.0)
    assert math.isclose(camera.forward.y, 0.0, abs_tol=1e-9)
    assert math.isclose(camera.forward.z, 0.0, abs_tol=1e-9)
