from __future__ import annotations

import pytest

from minipy3dr import Material, Mesh, PerspectiveCamera, Renderer, Scene
from minipy3dr.math import Vector3
from minipy3dr.render import NumpyFrameBuffer, Rasterizer, ZBuffer


class SurfaceStub:
    def __init__(self, size: tuple[int, int]) -> None:
        self.width, self.height = size
        self.pixels = [[(0, 0, 0) for _ in range(self.width)] for _ in range(self.height)]

    def fill(self, color: tuple[int, int, int]) -> None:
        for y in range(self.height):
            for x in range(self.width):
                self.pixels[y][x] = color

    def set_at(self, pos: tuple[int, int], color: tuple[int, int, int]) -> None:
        x, y = pos
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            raise IndexError(pos)
        self.pixels[y][x] = color

    def changed_pixels(self, background: tuple[int, int, int]) -> int:
        return sum(pixel != background for row in self.pixels for pixel in row)


def make_cube_scene() -> tuple[Scene, PerspectiveCamera]:
    scene = Scene()
    cube = Mesh.cube(size=2)
    cube.position = Vector3(0, 0, -5)
    cube.rotation = Vector3(0.2, 0.4, 0)
    scene.add(cube, Material(color=(200, 80, 60)))
    camera = PerspectiveCamera(fov=70, aspect=1, near=0.1, far=100)
    return scene, camera


def test_cube_wireframe_uses_outer_edges() -> None:
    assert len(Mesh.cube(size=2).edges()) == 12


def test_wireframe_render_changes_pixels() -> None:
    renderer = Renderer((96, 96))
    surface = SurfaceStub((96, 96))
    scene, camera = make_cube_scene()

    renderer.render(scene, camera, surface, mode="wireframe")

    assert surface.changed_pixels(renderer.background) > 0


def test_solid_render_changes_pixels() -> None:
    renderer = Renderer((96, 96))
    surface = SurfaceStub((96, 96))
    scene, camera = make_cube_scene()

    renderer.render(scene, camera, surface, mode="solid")

    assert surface.changed_pixels(renderer.background) > 0


def test_fast_solid_render_changes_pixels() -> None:
    pygame = pytest.importorskip("pygame")
    renderer = Renderer((96, 96))
    surface = pygame.Surface((96, 96))
    scene, camera = make_cube_scene()

    renderer.render(scene, camera, surface, mode="solid_fast")

    assert surface.get_at((48, 48)) != (*renderer.background, 255)


def test_numpy_solid_render_changes_pixels() -> None:
    pygame = pytest.importorskip("pygame")
    pytest.importorskip("numpy")
    renderer = Renderer((96, 96))
    surface = pygame.Surface((96, 96))
    scene, camera = make_cube_scene()

    renderer.render(scene, camera, surface, mode="solid_numpy")

    assert surface.get_at((48, 48)) != (*renderer.background, 255)


def test_zbuffer_keeps_nearest_triangle() -> None:
    surface = SurfaceStub((16, 16))
    zbuffer = ZBuffer(16, 16)

    Rasterizer.fill_triangle(
        surface,
        (2, 2, 0.8),
        (13, 2, 0.8),
        (2, 13, 0.8),
        (255, 0, 0),
        zbuffer,
    )
    Rasterizer.fill_triangle(
        surface,
        (2, 2, 0.2),
        (13, 2, 0.2),
        (2, 13, 0.2),
        (0, 0, 255),
        zbuffer,
    )

    assert surface.pixels[4][4] == (0, 0, 255)


def test_numpy_framebuffer_keeps_nearest_triangle() -> None:
    pytest.importorskip("numpy")
    framebuffer = NumpyFrameBuffer(16, 16, (0, 0, 0))

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

    assert tuple(framebuffer.color[4, 4]) == (0, 0, 255)
