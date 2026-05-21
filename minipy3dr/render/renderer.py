"""Software renderer that draws meshes directly into a pygame Surface."""

from __future__ import annotations

from collections.abc import Iterable

from minipy3dr.core import DirectionalLight, Material, Mesh, PerspectiveCamera, Scene
from minipy3dr.math import Matrix4, Vector3, Vector4
from minipy3dr.render.numpy_rasterizer import NumpyFrameBuffer
from minipy3dr.render.pipeline import ProjectedVertex, viewport_transform
from minipy3dr.render.rasterizer import Rasterizer
from minipy3dr.render.shader import PreparedDirectionalLight, flat_shade_prepared, prepare_lights
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
            prepared_lights = prepare_lights(scene.lights)
            view = camera.view_matrix()
            projection = camera.projection_matrix()

            for item in scene.items:
                if not item.mesh.visible:
                    continue
                if mode == "wireframe":
                    self.draw_wireframe(item.mesh, camera, target, item.material)
                else:
                    projected = self._project_mesh_with_matrices(
                        item.mesh,
                        view,
                        projection,
                        camera.near,
                        camera.far,
                    )
                    self._draw_projected_solid(target, projected, item.mesh.faces, item.material, prepared_lights)
        finally:
            if callable(unlock):
                unlock()

    def draw_solid_fast(self, scene: Scene, camera: PerspectiveCamera, target: object) -> None:
        import pygame

        prepared_lights = prepare_lights(scene.lights)
        view = camera.view_matrix()
        projection = camera.projection_matrix()
        triangles: list[tuple[float, tuple[int, int, int], list[tuple[float, float]]]] = []
        for item in scene.items:
            if not item.mesh.visible:
                continue

            projected = self._project_mesh_with_matrices(
                item.mesh,
                view,
                projection,
                camera.near,
                camera.far,
            )
            for index_a, index_b, index_c in item.mesh.faces:
                vertex_a = projected[index_a]
                vertex_b = projected[index_b]
                vertex_c = projected[index_c]
                screen_a = vertex_a.screen
                screen_b = vertex_b.screen
                screen_c = vertex_c.screen
                if screen_a is None or screen_b is None or screen_c is None:
                    continue
                if not self._is_front_facing(vertex_a.view, vertex_b.view, vertex_c.view):
                    continue

                color = self._shade_face(item.material, prepared_lights, vertex_a, vertex_b, vertex_c)
                points = [(screen_a[0], screen_a[1]), (screen_b[0], screen_b[1]), (screen_c[0], screen_c[1])]
                depth = (screen_a[2] + screen_b[2] + screen_c[2]) / 3.0
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
        prepared_lights = prepare_lights(scene.lights)
        view = camera.view_matrix()
        projection = camera.projection_matrix()
        for item in scene.items:
            if not item.mesh.visible:
                continue

            projected = self._project_mesh_with_matrices(
                item.mesh,
                view,
                projection,
                camera.near,
                camera.far,
            )
            for index_a, index_b, index_c in item.mesh.faces:
                vertex_a = projected[index_a]
                vertex_b = projected[index_b]
                vertex_c = projected[index_c]
                screen_a = vertex_a.screen
                screen_b = vertex_b.screen
                screen_c = vertex_c.screen
                if screen_a is None or screen_b is None or screen_c is None:
                    continue
                if not self._is_front_facing(vertex_a.view, vertex_b.view, vertex_c.view):
                    continue

                color = self._shade_face(item.material, prepared_lights, vertex_a, vertex_b, vertex_c)
                self.numpy_buffer.fill_triangle(
                    screen_a,
                    screen_b,
                    screen_c,
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
        lights: Iterable[DirectionalLight] = (),
    ) -> None:
        chosen_material = material or mesh.material or Material()
        prepared_lights = prepare_lights(lights)
        projected = self._project_mesh(mesh, camera)

        self._draw_projected_solid(target, projected, mesh.faces, chosen_material, prepared_lights)

    def _project_mesh(self, mesh: Mesh, camera: PerspectiveCamera) -> list[ProjectedVertex]:
        return self._project_mesh_with_matrices(
            mesh,
            camera.view_matrix(),
            camera.projection_matrix(),
            camera.near,
            camera.far,
        )

    def _project_mesh_with_matrices(
        self,
        mesh: Mesh,
        view: Matrix4,
        projection: Matrix4,
        near: float,
        far: float,
    ) -> list[ProjectedVertex]:
        world = mesh.local_matrix()
        result: list[ProjectedVertex] = []

        for vertex in mesh.vertices:
            world_vertex = world.transform_point(vertex)
            view_vertex = view.transform_point(world_vertex)
            screen = None
            if -far <= view_vertex.z <= -near:
                clip = projection @ Vector4(view_vertex.x, view_vertex.y, view_vertex.z, 1.0)
                if clip.w != 0:
                    ndc = Vector3(clip.x / clip.w, clip.y / clip.w, clip.z / clip.w)
                    screen = viewport_transform(ndc, self.width, self.height)
            result.append(ProjectedVertex(world_vertex, view_vertex, screen))

        return result

    def _draw_projected_solid(
        self,
        target: object,
        projected: list[ProjectedVertex],
        faces: list[tuple[int, int, int]],
        material: Material,
        lights: tuple[PreparedDirectionalLight, ...],
    ) -> None:
        for index_a, index_b, index_c in faces:
            vertex_a = projected[index_a]
            vertex_b = projected[index_b]
            vertex_c = projected[index_c]
            screen_a = vertex_a.screen
            screen_b = vertex_b.screen
            screen_c = vertex_c.screen
            if screen_a is None or screen_b is None or screen_c is None:
                continue
            if not self._is_front_facing(vertex_a.view, vertex_b.view, vertex_c.view):
                continue

            color = self._shade_face(material, lights, vertex_a, vertex_b, vertex_c)
            Rasterizer.fill_triangle(target, screen_a, screen_b, screen_c, color, self.zbuffer)

    @staticmethod
    def _shade_face(
        material: Material,
        lights: tuple[PreparedDirectionalLight, ...],
        vertex_a: ProjectedVertex,
        vertex_b: ProjectedVertex,
        vertex_c: ProjectedVertex,
    ) -> tuple[int, int, int]:
        return flat_shade_prepared(material, lights, vertex_a.world, vertex_b.world, vertex_c.world)

    @staticmethod
    def _is_front_facing(a: Vector3, b: Vector3, c: Vector3) -> bool:
        ab_x = b.x - a.x
        ab_y = b.y - a.y
        ab_z = b.z - a.z
        ac_x = c.x - a.x
        ac_y = c.y - a.y
        ac_z = c.z - a.z
        normal_x = ab_y * ac_z - ab_z * ac_y
        normal_y = ab_z * ac_x - ab_x * ac_z
        normal_z = ab_x * ac_y - ab_y * ac_x
        center_x = (a.x + b.x + c.x) / 3.0
        center_y = (a.y + b.y + c.y) / 3.0
        center_z = (a.z + b.z + c.z) / 3.0
        return normal_x * -center_x + normal_y * -center_y + normal_z * -center_z > 0
