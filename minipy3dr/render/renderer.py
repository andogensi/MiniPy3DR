"""Software renderer that draws meshes directly into a pygame Surface."""

from __future__ import annotations

from minipy3dr.core import Material, Mesh, PerspectiveCamera, Scene
from minipy3dr.math import Vector3, Vector4
from minipy3dr.render.numpy_rasterizer import NumpyFrameBuffer
from minipy3dr.render.pipeline import ProjectedVertex, viewport_transform
from minipy3dr.render.rasterizer import Rasterizer
from minipy3dr.render.zbuffer import ZBuffer


class Renderer:
    def __init__(
        self,
        size: tuple[int, int],
        background: tuple[int, int, int] = (16, 18, 24),
        wire_color: tuple[int, int, int] = (240, 244, 255),
    ) -> None:
        self.width, self.height = size
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Renderer size must be positive")
        self.background = background
        self.wire_color = wire_color
        self.zbuffer = ZBuffer(self.width, self.height)
        self.numpy_buffer = NumpyFrameBuffer(self.width, self.height, self.background)

    def render(
        self,
        scene: Scene,
        camera: PerspectiveCamera,
        target: object,
        mode: str = "solid",
    ) -> None:
        if mode not in {"solid", "solid_fast", "solid_numpy", "wireframe"}:
            raise ValueError('mode must be "solid", "solid_fast", "solid_numpy", or "wireframe"')

        if mode == "solid_fast":
            self.clear(target)
            self.draw_solid_fast(scene, camera, target)
            return
        if mode == "solid_numpy":
            self.draw_solid_numpy(scene, camera, target)
            return

        lock = getattr(target, "lock", None)
        unlock = getattr(target, "unlock", None)
        if callable(lock):
            lock()
        try:
            self.clear(target)
            self.zbuffer.clear()

            for item in scene.items:
                if not item.mesh.visible:
                    continue
                if mode == "wireframe":
                    self.draw_wireframe(item.mesh, camera, target, item.material)
                else:
                    self.draw_solid(item.mesh, camera, target, item.material)
        finally:
            if callable(unlock):
                unlock()

    def draw_solid_fast(self, scene: Scene, camera: PerspectiveCamera, target: object) -> None:
        import pygame

        triangles: list[tuple[float, tuple[int, int, int], list[tuple[float, float]]]] = []
        for item in scene.items:
            if not item.mesh.visible:
                continue

            projected = self._project_mesh(item.mesh, camera)
            color = item.material.color
            for face in item.mesh.faces:
                vertices = [projected[index] for index in face]
                if any(vertex.screen is None for vertex in vertices):
                    continue
                if not self._is_front_facing(vertices[0].view, vertices[1].view, vertices[2].view):
                    continue

                points = [(vertex.screen[0], vertex.screen[1]) for vertex in vertices]
                depth = sum(vertex.screen[2] for vertex in vertices) / 3.0
                triangles.append((depth, color, points))

        for _, color, points in sorted(triangles, key=lambda triangle: triangle[0], reverse=True):
            pygame.draw.polygon(target, color, points)

    def draw_solid_numpy(self, scene: Scene, camera: PerspectiveCamera, target: object) -> None:
        self.clear_numpy_buffer()
        self.draw_solid_numpy_scene(scene, camera)
        self.blit_numpy_buffer(target)

    def clear_numpy_buffer(self) -> None:
        self.numpy_buffer.clear(self.background)

    def draw_solid_numpy_scene(self, scene: Scene, camera: PerspectiveCamera) -> None:
        for item in scene.items:
            if not item.mesh.visible:
                continue

            projected = self._project_mesh(item.mesh, camera)
            color = item.material.color
            for face in item.mesh.faces:
                vertices = [projected[index] for index in face]
                if any(vertex.screen is None for vertex in vertices):
                    continue
                if not self._is_front_facing(vertices[0].view, vertices[1].view, vertices[2].view):
                    continue

                self.numpy_buffer.fill_triangle(
                    vertices[0].screen,
                    vertices[1].screen,
                    vertices[2].screen,
                    color,
                )

    def blit_numpy_buffer(self, target: object) -> None:
        self.numpy_buffer.blit_to_surface(target)

    def clear(self, target: object) -> None:
        if hasattr(target, "fill"):
            target.fill(self.background)
            return

        for y in range(self.height):
            for x in range(self.width):
                target.set_at((x, y), self.background)

    def draw_wireframe(
        self,
        mesh: Mesh,
        camera: PerspectiveCamera,
        target: object,
        material: Material | None = None,
    ) -> None:
        projected = self._project_mesh(mesh, camera)
        color = material.color if material else self.wire_color
        for start_index, end_index in mesh.edges():
            start = projected[start_index].screen
            end = projected[end_index].screen
            if start is None or end is None:
                continue
            Rasterizer.draw_line(target, (start[0], start[1]), (end[0], end[1]), color)

    def draw_solid(
        self,
        mesh: Mesh,
        camera: PerspectiveCamera,
        target: object,
        material: Material | None = None,
    ) -> None:
        projected = self._project_mesh(mesh, camera)
        color = (material or mesh.material or Material()).color

        for face in mesh.faces:
            vertices = [projected[index] for index in face]
            if any(vertex.screen is None for vertex in vertices):
                continue
            if not self._is_front_facing(vertices[0].view, vertices[1].view, vertices[2].view):
                continue

            Rasterizer.fill_triangle(
                target,
                vertices[0].screen,
                vertices[1].screen,
                vertices[2].screen,
                color,
                self.zbuffer,
            )

    def _project_mesh(self, mesh: Mesh, camera: PerspectiveCamera) -> list[ProjectedVertex]:
        world = mesh.local_matrix()
        view = camera.view_matrix()
        projection = camera.projection_matrix()
        result: list[ProjectedVertex] = []

        for vertex in mesh.vertices:
            world_vertex = world.transform_point(vertex)
            view_vertex = view.transform_point(world_vertex)
            screen = None
            if -camera.far <= view_vertex.z <= -camera.near:
                clip = projection @ Vector4(view_vertex.x, view_vertex.y, view_vertex.z, 1.0)
                if clip.w != 0:
                    ndc = Vector3(clip.x / clip.w, clip.y / clip.w, clip.z / clip.w)
                    screen = viewport_transform(ndc, self.width, self.height)
            result.append(ProjectedVertex(view_vertex, screen))

        return result

    @staticmethod
    def _is_front_facing(a: Vector3, b: Vector3, c: Vector3) -> bool:
        normal = (b - a).cross(c - a)
        center = (a + b + c) / 3.0
        return normal.dot(-center) > 0
