from __future__ import annotations

import pytest

from minipy3dr import DirectionalLight, Material, Mesh, PerspectiveCamera, Renderer, Scene
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


def test_directional_light_flat_shades_front_face() -> None:
    renderer = Renderer((64, 64))
    surface = SurfaceStub((64, 64))
    scene, camera = make_triangle_scene(Vector3(0, 0, -1))

    renderer.render(scene, camera, surface, mode="solid")

    assert surface.pixels[32][32] == (100, 50, 20)


def test_directional_light_uses_ambient_for_unlit_face() -> None:
    renderer = Renderer((64, 64))
    surface = SurfaceStub((64, 64))
    scene, camera = make_triangle_scene(Vector3(0, 0, 1))

    renderer.render(scene, camera, surface, mode="solid")

    assert surface.pixels[32][32] == (25, 12, 5)


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


def test_native_solid_path_uses_one_scene_render_call() -> None:
    class NativeBufferSpy:
        def __init__(self) -> None:
            self.render_scene_calls = 0
            self.clear_calls = 0
            self.blit_calls = 0

        def clear(self, background: tuple[int, int, int]) -> None:
            del background
            self.clear_calls += 1

        def render_scene(self, *args: object) -> None:
            self.render_scene_calls += 1
            assert len(args) == 15

        def blit_to_surface(self, target: object) -> None:
            del target
            self.blit_calls += 1

    renderer = Renderer((96, 96))
    renderer.native_buffer = NativeBufferSpy()  # type: ignore[assignment]
    scene, camera = make_cube_scene()

    renderer.draw_solid_native(scene, camera, object())

    assert renderer.native_buffer.render_scene_calls == 1  # type: ignore[union-attr]
    assert renderer.native_buffer.clear_calls == 0  # type: ignore[union-attr]
    assert renderer.native_buffer.blit_calls == 1  # type: ignore[union-attr]


def test_renderer_culls_meshes_outside_view() -> None:
    pytest.importorskip("numpy")
    renderer = Renderer((96, 96))
    scene = Scene()
    visible = Mesh.cube(size=1)
    visible.position = Vector3(0, 0, -5)
    hidden = Mesh.cube(size=1)
    hidden.position = Vector3(1000, 0, -5)
    scene.add(visible, Material(color=(255, 0, 0)))
    scene.add(hidden, Material(color=(0, 255, 0)))
    camera = PerspectiveCamera(fov=70, aspect=1, near=0.1, far=100)
    projected_meshes: list[Mesh] = []
    original_project = renderer._project_mesh_with_matrices

    def project_spy(
        mesh: Mesh,
        view: object,
        projection: object,
        near: float,
        far: float,
    ) -> object:
        projected_meshes.append(mesh)
        return original_project(mesh, view, projection, near, far)

    renderer._project_mesh_with_matrices = project_spy  # type: ignore[method-assign]

    renderer.draw_solid_numpy_scene(scene, camera)

    assert any(mesh is visible for mesh in projected_meshes)
    assert all(mesh is not hidden for mesh in projected_meshes)


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
