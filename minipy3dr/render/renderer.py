"""Software renderer that draws meshes directly into a pygame Surface."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import math

from minipy3dr.core import DirectionalLight, Material, Mesh, PerspectiveCamera, Scene
from minipy3dr.math import Matrix4, Vector3
from minipy3dr.render.native_rasterizer import NativeFrameBuffer, is_native_available
from minipy3dr.render.numpy_rasterizer import NumpyFrameBuffer
from minipy3dr.render.pipeline import ProjectedVertex
from minipy3dr.render.rasterizer import Rasterizer
from minipy3dr.render.shader import PreparedDirectionalLight, flat_shade_prepared, prepare_lights
from minipy3dr.render.zbuffer import ZBuffer


@dataclass
class _NativeSceneCache:
    key: tuple[object, ...]
    vertices: object
    faces: object
    mesh_ranges: object
    mesh_states: object
    materials: object
    lights: object
    items: tuple[object, ...]


_RENDER_MODES = {"solid", "solid_fast", "solid_numpy", "solid_native", "wireframe"}
_RENDER_MODE_ALIASES = {
    "fast": "solid_fast",
    "native": "solid_native",
    "numpy": "solid_numpy",
    "wire": "wireframe",
}


def resolve_render_mode(mode: str) -> str:
    """Return the concrete renderer mode for user-facing aliases."""

    normalized = mode.strip().lower()
    if normalized == "auto":
        return "solid_native" if is_native_available() else "solid_numpy"
    normalized = _RENDER_MODE_ALIASES.get(normalized, normalized)
    if normalized not in _RENDER_MODES:
        valid = ", ".join(sorted((*_RENDER_MODES, *_RENDER_MODE_ALIASES, "auto")))
        raise ValueError(f"mode must be one of: {valid}")
    return normalized


class Renderer:
    def __init__(
        self,
        size: tuple[int, int],
        background: tuple[int, int, int] = (16, 18, 24),
        wire_color: tuple[int, int, int] = (240, 244, 255),
        mode: str = "solid",
    ) -> None:
        self.width, self.height = size
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Renderer size must be positive")
        self.background = background
        self.wire_color = wire_color
        self.mode = resolve_render_mode(mode)
        self.zbuffer = ZBuffer(self.width, self.height)
        self.numpy_buffer = NumpyFrameBuffer(self.width, self.height, self.background)
        self.native_buffer: NativeFrameBuffer | None = None
        self._native_scene_cache: _NativeSceneCache | None = None
        self.enable_mesh_culling = True
        self.mesh_cull_distance: float | None = None

    def render(
        self,
        scene: Scene,
        camera: PerspectiveCamera,
        target: object,
        mode: str | None = None,
    ) -> None:
        mode = self.mode if mode is None else resolve_render_mode(mode)

        if mode == "solid_fast":
            self.clear(target)
            self.draw_solid_fast(scene, camera, target)
            return
        if mode == "solid_numpy":
            self.draw_solid_numpy(scene, camera, target)
            return
        if mode == "solid_native":
            self.draw_solid_native(scene, camera, target)
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
            culling = self._mesh_culling_context(camera, view)

            for item in scene.items:
                if not item.mesh.visible:
                    continue
                if self._should_cull_mesh(item.mesh, culling):
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
        culling = self._mesh_culling_context(camera, view)
        triangles: list[tuple[float, tuple[int, int, int], list[tuple[float, float]]]] = []
        for item in scene.items:
            if not item.mesh.visible:
                continue
            if self._should_cull_mesh(item.mesh, culling):
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
        culling = self._mesh_culling_context(camera, view)
        for item in scene.items:
            if not item.mesh.visible:
                continue
            if self._should_cull_mesh(item.mesh, culling):
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

    def draw_solid_native(self, scene: Scene, camera: PerspectiveCamera, target: object) -> None:
        self.draw_solid_native_scene(scene, camera)
        self.blit_native_buffer(target)

    def clear_native_buffer(self) -> None:
        self._native_framebuffer().clear(self.background)

    def draw_solid_native_scene(self, scene: Scene, camera: PerspectiveCamera) -> None:
        native_buffer = self._native_framebuffer()
        view = camera.view_matrix()
        projection = camera.projection_matrix()
        culling = self._mesh_culling_context(camera, view)
        if culling is None:
            enable_culling = False
            cull_far = camera.far
            vertical_tan = 0.0
            horizontal_tan = 0.0
        else:
            _, _, cull_far, vertical_tan, horizontal_tan = culling
            enable_culling = True

        (
            vertices,
            faces,
            mesh_ranges,
            mesh_states,
            materials,
            lights,
        ) = self._pack_native_scene(scene)
        native_buffer.render_scene(
            vertices,
            faces,
            mesh_ranges,
            mesh_states,
            materials,
            lights,
            self._matrix_to_native_array(view),
            self._matrix_to_native_array(projection),
            self.background,
            camera.near,
            camera.far,
            cull_far,
            vertical_tan,
            horizontal_tan,
            enable_culling,
        )

    def blit_native_buffer(self, target: object) -> None:
        self._native_framebuffer().blit_to_surface(target)

    def _native_framebuffer(self) -> NativeFrameBuffer:
        if self.native_buffer is None:
            if not is_native_available():
                raise RuntimeError("native rasterizer is not built")
            self.native_buffer = NativeFrameBuffer(self.width, self.height, self.background)
        return self.native_buffer

    def _pack_native_scene(self, scene: Scene) -> tuple[object, object, object, object, object, object]:
        import numpy as np

        items = tuple(item for item in scene.items if item.mesh.visible and item.mesh.vertices and item.mesh.faces)
        key = self._native_scene_cache_key(items, scene.lights)
        cache = self._native_scene_cache
        if cache is None or cache.key != key:
            vertex_count = sum(len(item.mesh.vertices) for item in items)
            face_count = sum(len(item.mesh.faces) for item in items)
            mesh_count = len(items)

            vertices = np.empty((vertex_count, 3), dtype=np.float64)
            faces = np.empty((face_count, 3), dtype=np.int32)
            mesh_ranges = np.empty((mesh_count, 5), dtype=np.int32)
            mesh_states = np.empty((mesh_count, 10), dtype=np.float64)
            materials = np.empty((mesh_count, 4), dtype=np.float64)
            lights = np.empty((len(scene.lights), 7), dtype=np.float64)

            vertex_offset = 0
            face_offset = 0
            for mesh_index, item in enumerate(items):
                mesh = item.mesh
                for vertex_index, vertex in enumerate(mesh.vertices):
                    vertices[vertex_offset + vertex_index] = (vertex.x, vertex.y, vertex.z)
                for local_face_index, face in enumerate(mesh.faces):
                    faces[face_offset + local_face_index] = face

                mesh_ranges[mesh_index] = (
                    vertex_offset,
                    len(mesh.vertices),
                    face_offset,
                    len(mesh.faces),
                    mesh_index,
                )

                vertex_offset += len(mesh.vertices)
                face_offset += len(mesh.faces)

            cache = _NativeSceneCache(
                key=key,
                vertices=vertices,
                faces=faces,
                mesh_ranges=mesh_ranges,
                mesh_states=mesh_states,
                materials=materials,
                lights=lights,
                items=items,
            )
            self._native_scene_cache = cache

        for mesh_index, item in enumerate(cache.items):
            mesh = item.mesh
            material = item.material
            cache.mesh_states[mesh_index] = (
                mesh.position.x,
                mesh.position.y,
                mesh.position.z,
                mesh.rotation.x,
                mesh.rotation.y,
                mesh.rotation.z,
                mesh.scale.x,
                mesh.scale.y,
                mesh.scale.z,
                self._mesh_local_radius(mesh),
            )
            cache.materials[mesh_index] = (
                material.color[0],
                material.color[1],
                material.color[2],
                material.ambient,
            )

        for light_index, light in enumerate(scene.lights):
            cache.lights[light_index] = (
                light.direction.x,
                light.direction.y,
                light.direction.z,
                light.color[0],
                light.color[1],
                light.color[2],
                light.intensity,
            )

        return cache.vertices, cache.faces, cache.mesh_ranges, cache.mesh_states, cache.materials, cache.lights

    @staticmethod
    def _native_scene_cache_key(items: tuple[object, ...], lights: tuple[DirectionalLight, ...]) -> tuple[object, ...]:
        mesh_keys = tuple(
            (
                id(item.mesh),
                id(item.mesh.vertices),
                len(item.mesh.vertices),
                id(item.mesh.faces),
                len(item.mesh.faces),
                id(item.material),
            )
            for item in items
        )
        light_keys = tuple(id(light) for light in lights)
        return mesh_keys, light_keys

    @staticmethod
    def _matrix_to_native_array(matrix: Matrix4) -> object:
        import numpy as np

        return np.asarray(matrix.rows, dtype=np.float64).reshape(16)

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
        world_0, world_1, world_2 = world.rows[0], world.rows[1], world.rows[2]
        view_0, view_1, view_2 = view.rows[0], view.rows[1], view.rows[2]
        projection_0, projection_1, projection_2, projection_3 = projection.rows
        viewport_x_scale = 0.5 * (self.width - 1)
        viewport_y_scale = 0.5 * (self.height - 1)
        result: list[ProjectedVertex] = []
        append = result.append

        for vertex in mesh.vertices:
            x, y, z = vertex.x, vertex.y, vertex.z
            world_x = world_0[0] * x + world_0[1] * y + world_0[2] * z + world_0[3]
            world_y = world_1[0] * x + world_1[1] * y + world_1[2] * z + world_1[3]
            world_z = world_2[0] * x + world_2[1] * y + world_2[2] * z + world_2[3]
            view_x = view_0[0] * world_x + view_0[1] * world_y + view_0[2] * world_z + view_0[3]
            view_y = view_1[0] * world_x + view_1[1] * world_y + view_1[2] * world_z + view_1[3]
            view_z = view_2[0] * world_x + view_2[1] * world_y + view_2[2] * world_z + view_2[3]
            screen = None
            if -far <= view_z <= -near:
                clip_x = (
                    projection_0[0] * view_x
                    + projection_0[1] * view_y
                    + projection_0[2] * view_z
                    + projection_0[3]
                )
                clip_y = (
                    projection_1[0] * view_x
                    + projection_1[1] * view_y
                    + projection_1[2] * view_z
                    + projection_1[3]
                )
                clip_z = (
                    projection_2[0] * view_x
                    + projection_2[1] * view_y
                    + projection_2[2] * view_z
                    + projection_2[3]
                )
                clip_w = (
                    projection_3[0] * view_x
                    + projection_3[1] * view_y
                    + projection_3[2] * view_z
                    + projection_3[3]
                )
                if clip_w != 0:
                    inv_w = 1.0 / clip_w
                    ndc_x = clip_x * inv_w
                    ndc_y = clip_y * inv_w
                    ndc_z = clip_z * inv_w
                    screen = (
                        (ndc_x + 1.0) * viewport_x_scale,
                        (1.0 - ndc_y) * viewport_y_scale,
                        (ndc_z + 1.0) * 0.5,
                    )
            append(
                ProjectedVertex(
                    Vector3(world_x, world_y, world_z),
                    Vector3(view_x, view_y, view_z),
                    screen,
                )
            )

        return result

    def _mesh_culling_context(
        self,
        camera: PerspectiveCamera,
        view: Matrix4,
    ) -> tuple[Matrix4, float, float, float, float] | None:
        if not self.enable_mesh_culling:
            return None

        max_distance = camera.far
        if self.mesh_cull_distance is not None:
            max_distance = min(max_distance, self.mesh_cull_distance)
        if max_distance <= camera.near:
            max_distance = camera.far

        vertical_tan = math.tan(math.radians(camera.fov) * 0.5)
        horizontal_tan = vertical_tan * camera.aspect
        return (view, camera.near, max_distance, vertical_tan, horizontal_tan)

    def _should_cull_mesh(
        self,
        mesh: Mesh,
        culling: tuple[Matrix4, float, float, float, float] | None,
    ) -> bool:
        if culling is None:
            return False
        if not mesh.vertices:
            return True

        view, near, far, vertical_tan, horizontal_tan = culling
        radius = self._mesh_world_radius(mesh)
        view_x, view_y, view_z = self._transform_position_to_view(mesh.position, view)

        if view_z - radius > -near:
            return True
        if view_z + radius < -far:
            return True

        depth = max(near, -view_z)
        if abs(view_x) > depth * horizontal_tan + radius:
            return True
        if abs(view_y) > depth * vertical_tan + radius:
            return True
        return False

    @staticmethod
    def _mesh_world_radius(mesh: Mesh) -> float:
        local_radius_sq = Renderer._mesh_local_radius(mesh) ** 2
        scale = max(abs(mesh.scale.x), abs(mesh.scale.y), abs(mesh.scale.z))
        return math.sqrt(local_radius_sq) * scale

    @staticmethod
    def _mesh_local_radius(mesh: Mesh) -> float:
        local_radius_sq = 0.0
        for vertex in mesh.vertices:
            radius_sq = vertex.x * vertex.x + vertex.y * vertex.y + vertex.z * vertex.z
            if radius_sq > local_radius_sq:
                local_radius_sq = radius_sq
        return math.sqrt(local_radius_sq)

    @staticmethod
    def _transform_position_to_view(position: Vector3, view: Matrix4) -> tuple[float, float, float]:
        x, y, z = position.x, position.y, position.z
        row_0, row_1, row_2 = view.rows[0], view.rows[1], view.rows[2]
        return (
            row_0[0] * x + row_0[1] * y + row_0[2] * z + row_0[3],
            row_1[0] * x + row_1[1] * y + row_1[2] * z + row_1[3],
            row_2[0] * x + row_2[1] * y + row_2[2] * z + row_2[3],
        )

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


class NativeRenderer(Renderer):
    """Renderer that uses the native C++ path by default."""

    def __init__(
        self,
        size: tuple[int, int],
        background: tuple[int, int, int] = (16, 18, 24),
        wire_color: tuple[int, int, int] = (240, 244, 255),
    ) -> None:
        super().__init__(
            size=size,
            background=background,
            wire_color=wire_color,
            mode="native",
        )
