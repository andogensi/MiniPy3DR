from __future__ import annotations

import pytest

from minipy3dr import DirectionalLight, Material, Mesh, PerspectiveCamera, Renderer, Scene
from minipy3dr.math import Vector3
from minipy3dr.render import NativeFrameBuffer, is_native_available


pytestmark = pytest.mark.skipif(not is_native_available(), reason="native rasterizer is not built")


def make_triangle_scene(light_direction: Vector3) -> tuple[Scene, PerspectiveCamera]:
    scene = Scene()
    triangle = Mesh(
        vertices=[
            Vector3(-1, -1, -3),
            Vector3(1, -1, -3),
            Vector3(0, 1, -3),
        ],
        faces=[(0, 1, 2)],
    )
    scene.add(triangle, Material(color=(100, 50, 20), ambient=0.25))
    scene.add_light(DirectionalLight(direction=light_direction))
    camera = PerspectiveCamera(fov=90, aspect=1, near=0.1, far=100)
    return scene, camera


def test_native_framebuffer_keeps_nearest_triangle() -> None:
    framebuffer = NativeFrameBuffer(16, 16, (0, 0, 0))

    framebuffer.fill_triangle(
        (2, 2, 0.8),
        (13, 2, 0.8),
        (2, 13, 0.8),
        (255, 0, 0),
    )
    framebuffer.fill_triangle(
        (2, 2, 0.2),
        (13, 2, 0.2),
        (2, 13, 0.2),
        (0, 0, 255),
    )

    assert framebuffer.get_pixel(4, 4) == (0, 0, 255)


def test_native_framebuffer_batches_triangles() -> None:
    framebuffer = NativeFrameBuffer(16, 16, (0, 0, 0))

    framebuffer.fill_triangles(
        [
            ((2, 2, 0.8), (13, 2, 0.8), (2, 13, 0.8), (255, 0, 0)),
            ((2, 2, 0.2), (13, 2, 0.2), (2, 13, 0.2), (0, 0, 255)),
        ]
    )

    assert framebuffer.get_pixel(4, 4) == (0, 0, 255)


def test_native_solid_render_changes_pixels() -> None:
    pygame = pytest.importorskip("pygame")
    renderer = Renderer((96, 96))
    surface = pygame.Surface((96, 96))
    scene = Scene()
    cube = Mesh.cube(size=2)
    cube.position = Vector3(0, 0, -5)
    cube.rotation = Vector3(0.2, 0.4, 0)
    scene.add(cube, Material(color=(200, 80, 60)))
    camera = PerspectiveCamera(fov=70, aspect=1, near=0.1, far=100)

    renderer.render(scene, camera, surface, mode="solid_native")

    assert surface.get_at((48, 48)) != (*renderer.background, 255)


def test_native_directional_light_flat_shades_front_face() -> None:
    pygame = pytest.importorskip("pygame")
    renderer = Renderer((64, 64))
    surface = pygame.Surface((64, 64))
    scene, camera = make_triangle_scene(Vector3(0, 0, -1))

    renderer.render(scene, camera, surface, mode="solid_native")

    assert surface.get_at((32, 32)) == (100, 50, 20, 255)


def test_native_directional_light_uses_ambient_for_unlit_face() -> None:
    pygame = pytest.importorskip("pygame")
    renderer = Renderer((64, 64))
    surface = pygame.Surface((64, 64))
    scene, camera = make_triangle_scene(Vector3(0, 0, 1))

    renderer.render(scene, camera, surface, mode="solid_native")

    assert surface.get_at((32, 32)) == (25, 12, 5, 255)


def test_native_clips_triangle_crossing_near_plane() -> None:
    pygame = pytest.importorskip("pygame")
    renderer = Renderer((64, 64))
    surface = pygame.Surface((64, 64))
    scene = Scene()
    triangle = Mesh(
        vertices=[
            Vector3(-0.8, -0.6, -0.05),
            Vector3(0.8, -0.6, -0.3),
            Vector3(0.0, 0.8, -0.3),
        ],
        faces=[(0, 1, 2)],
    )
    scene.add(triangle, Material(color=(210, 90, 60), ambient=1.0))
    camera = PerspectiveCamera(fov=90, aspect=1, near=0.1, far=10)

    renderer.render(scene, camera, surface, mode="solid_native")

    assert surface.get_at((32, 32)) != (*renderer.background, 255)
