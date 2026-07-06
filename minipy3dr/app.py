"""High-level pygame app wrapper for MiniPy3DR."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from os import PathLike

from minipy3dr.core import DirectionalLight, Material, Mesh, PerspectiveCamera, Scene
from minipy3dr.loaders import load_obj
from minipy3dr.math import Vector3
from minipy3dr.render import Renderer


UpdateCallback = Callable[["MiniPy3DRApp", float], None]
EventCallback = Callable[[object, "MiniPy3DRApp"], None]
OverlayCallback = Callable[["MiniPy3DRApp"], None]
VectorLike = Vector3 | tuple[float, float, float]
SizeLike = float | VectorLike


@dataclass
class AppObject:
    """A small handle for moving one or more meshes as a named object."""

    meshes: tuple[Mesh, ...]
    scene: Scene | None = None
    name: str = ""

    def __post_init__(self) -> None:
        if not self.meshes:
            raise ValueError("AppObject needs at least one mesh")

    @property
    def mesh(self) -> Mesh:
        return self.meshes[0]

    @property
    def position(self) -> Vector3:
        return self.mesh.position

    @position.setter
    def position(self, value: VectorLike) -> None:
        self.set_position(value)

    @property
    def rotation(self) -> Vector3:
        return self.mesh.rotation

    @rotation.setter
    def rotation(self, value: VectorLike) -> None:
        self.set_rotation(value)

    @property
    def visible(self) -> bool:
        return any(mesh.visible for mesh in self.meshes)

    @visible.setter
    def visible(self, value: bool) -> None:
        for mesh in self.meshes:
            mesh.visible = value

    def move(self, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> AppObject:
        delta = Vector3(x, y, z)
        for mesh in self.meshes:
            mesh.position = mesh.position + delta
        return self

    def rotate(self, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> AppObject:
        delta = Vector3(x, y, z)
        for mesh in self.meshes:
            mesh.rotation = mesh.rotation + delta
        return self

    def set_position(self, position: VectorLike) -> AppObject:
        new_position = vec3(position)
        delta = new_position - self.position
        return self.move(delta.x, delta.y, delta.z)

    def set_rotation(self, rotation: VectorLike) -> AppObject:
        new_rotation = vec3(rotation)
        for mesh in self.meshes:
            mesh.rotation = new_rotation
        return self

    def set_scale(self, scale: VectorLike) -> AppObject:
        new_scale = vec3(scale)
        for mesh in self.meshes:
            mesh.scale = new_scale
        return self

    def scale_by(self, x: float = 1.0, y: float = 1.0, z: float = 1.0) -> AppObject:
        for mesh in self.meshes:
            mesh.scale = Vector3(mesh.scale.x * x, mesh.scale.y * y, mesh.scale.z * z)
        return self

    def set_material(self, material: Material) -> AppObject:
        for mesh in self.meshes:
            if self.scene is not None:
                self.scene.set_material(mesh, material)
            else:
                mesh.material = material
        return self

    def set_color(
        self,
        color: tuple[int, int, int],
        ambient: float | None = None,
    ) -> AppObject:
        current = self.mesh.material or Material()
        return self.set_material(Material(color=color, ambient=current.ambient if ambient is None else ambient))

    def show(self) -> AppObject:
        self.visible = True
        return self

    def hide(self) -> AppObject:
        self.visible = False
        return self

    def remove(self) -> bool:
        if self.scene is None:
            return False
        removed = False
        for mesh in self.meshes:
            removed = self.scene.remove(mesh) or removed
        return removed

    def distance_to(self, other: SceneTarget | VectorLike) -> float:
        return (_target_position(self) - _target_position(other)).length()

    def overlaps(self, other: SceneTarget | VectorLike, padding: float = 0.0) -> bool:
        if isinstance(other, Vector3) or isinstance(other, tuple):
            return _point_in_bounds(vec3(other), self.bounds, padding)
        return _bounds_overlap(self.bounds, _target_bounds(other), padding)

    @property
    def bounds(self) -> tuple[Vector3, Vector3]:
        return _target_bounds(self)


SceneTarget = Mesh | AppObject


@dataclass(frozen=True)
class AppFrame:
    delta: float
    time: float
    index: int


class MiniPy3DRApp:
    """A small pygame-backed runtime for MiniPy3DR scenes."""

    def __init__(
        self,
        size: tuple[int, int] = (800, 600),
        title: str = "MiniPy3DR",
        render_scale: float = 1.0,
        background: tuple[int, int, int] = (16, 18, 24),
        mode: str = "auto",
        fps: int = 60,
        fov: float = 70.0,
        near: float = 0.1,
        far: float = 1000.0,
    ) -> None:
        if render_scale <= 0:
            raise ValueError("render_scale must be greater than 0")

        import pygame

        pygame.init()
        self.pygame = pygame
        self.size = size
        self.render_size = (
            max(1, int(size[0] * render_scale)),
            max(1, int(size[1] * render_scale)),
        )
        self.fps = fps
        self.screen = pygame.display.set_mode(size)
        self.render_surface = (
            self.screen if self.render_size == size else pygame.Surface(self.render_size)
        )
        pygame.display.set_caption(title)
        self.clock = pygame.time.Clock()
        self.renderer = Renderer(self.render_size, background=background, mode=mode)
        self.mode = self.renderer.mode
        self.scene = Scene()
        self.camera = PerspectiveCamera(
            fov=fov,
            aspect=self.render_size[0] / self.render_size[1],
            near=near,
            far=far,
        )
        self.running = True
        self.delta = 0.0
        self.time = 0.0
        self.frame_index = 0
        self._keys: object | None = None
        self._font_cache: dict[tuple[str, int, bool], object] = {}
        self._text_cache: dict[tuple[str, tuple[int, int, int], str, int, bool], object] = {}

    @property
    def frame(self) -> AppFrame:
        return AppFrame(self.delta, self.time, self.frame_index)

    def add(self, mesh: Mesh, material: Material | None = None) -> Mesh:
        return self.scene.add(mesh, material)

    def remove(self, target: SceneTarget) -> bool:
        if isinstance(target, AppObject):
            return target.remove()
        return self.scene.remove(target)

    def cube(
        self,
        position: Vector3 | tuple[float, float, float] = (0.0, 0.0, -5.0),
        scale: Vector3 | tuple[float, float, float] = (1.0, 1.0, 1.0),
        rotation: Vector3 | tuple[float, float, float] = (0.0, 0.0, 0.0),
        size: float = 1.0,
        material: Material | None = None,
        color: tuple[int, int, int] | None = None,
        ambient: float | None = None,
    ) -> Mesh:
        mesh = Mesh.cube(size=size)
        mesh.position = vec3(position)
        mesh.scale = vec3(scale)
        mesh.rotation = vec3(rotation)
        chosen_material = material
        if chosen_material is None and color is not None:
            chosen_material = Material(color=color, ambient=0.18 if ambient is None else ambient)
        return self.add(mesh, chosen_material)

    def box(
        self,
        position: VectorLike = (0.0, 0.0, -5.0),
        size: SizeLike = 1.0,
        rotation: VectorLike = (0.0, 0.0, 0.0),
        material: Material | None = None,
        color: tuple[int, int, int] | None = None,
        ambient: float | None = None,
        width: float | None = None,
        height: float | None = None,
        depth: float | None = None,
    ) -> Mesh:
        dimensions = size3(size)
        if width is not None:
            dimensions = Vector3(width, dimensions.y, dimensions.z)
        if height is not None:
            dimensions = Vector3(dimensions.x, height, dimensions.z)
        if depth is not None:
            dimensions = Vector3(dimensions.x, dimensions.y, depth)

        mesh = Mesh.cube(size=1.0)
        mesh.position = vec3(position)
        mesh.scale = dimensions
        mesh.rotation = vec3(rotation)
        return self.add(mesh, make_material(material, color, ambient))

    def sphere(
        self,
        position: VectorLike = (0.0, 0.0, -5.0),
        radius: float = 1.0,
        scale: VectorLike = (1.0, 1.0, 1.0),
        rotation: VectorLike = (0.0, 0.0, 0.0),
        segments: int = 16,
        rings: int = 8,
        material: Material | None = None,
        color: tuple[int, int, int] | None = None,
        ambient: float | None = None,
    ) -> Mesh:
        mesh = Mesh.sphere(radius=radius, segments=segments, rings=rings)
        mesh.position = vec3(position)
        mesh.scale = vec3(scale)
        mesh.rotation = vec3(rotation)
        return self.add(mesh, make_material(material, color, ambient))

    def floor(
        self,
        position: VectorLike = (0.0, -2.0, -5.0),
        width: float = 8.0,
        depth: float = 8.0,
        thickness: float = 0.1,
        color: tuple[int, int, int] | None = (80, 90, 110),
        material: Material | None = None,
        ambient: float | None = 0.28,
    ) -> Mesh:
        return self.box(
            position=position,
            size=(width, thickness, depth),
            color=color,
            material=material,
            ambient=ambient,
        )

    def wall(
        self,
        position: VectorLike = (0.0, 0.0, -8.0),
        width: float = 8.0,
        height: float = 3.0,
        thickness: float = 0.1,
        axis: str = "x",
        color: tuple[int, int, int] | None = (120, 130, 150),
        material: Material | None = None,
        ambient: float | None = 0.24,
    ) -> Mesh:
        if axis.lower() == "x":
            size = (width, height, thickness)
        elif axis.lower() == "z":
            size = (thickness, height, width)
        else:
            raise ValueError('axis must be "x" or "z"')
        return self.box(position=position, size=size, color=color, material=material, ambient=ambient)

    def actor(
        self,
        name: str = "",
        position: VectorLike = (0.0, 0.0, -5.0),
        size: SizeLike = 1.0,
        color: tuple[int, int, int] | None = None,
        ambient: float | None = None,
    ) -> AppObject:
        return self.object(
            self.box(position=position, size=size, color=color, ambient=ambient),
            name=name,
        )

    def object(self, target: SceneTarget | Iterable[SceneTarget], name: str = "") -> AppObject:
        if isinstance(target, Mesh) or isinstance(target, AppObject):
            meshes = _target_meshes(target)
        else:
            meshes = tuple(mesh for item in target for mesh in _target_meshes(item))
        return AppObject(meshes=meshes, scene=self.scene, name=name)

    def group(self, *targets: SceneTarget, name: str = "") -> AppObject:
        return self.object(targets, name=name)

    def obj(
        self,
        path: str | PathLike[str],
        position: Vector3 | tuple[float, float, float] = (0.0, 0.0, -5.0),
        scale: Vector3 | tuple[float, float, float] = (1.0, 1.0, 1.0),
        rotation: Vector3 | tuple[float, float, float] = (0.0, 0.0, 0.0),
        material: Material | None = None,
        color: tuple[int, int, int] | None = None,
        ambient: float | None = None,
    ) -> Mesh:
        chosen_material = material
        if chosen_material is None and color is not None:
            chosen_material = Material(color=color, ambient=0.18 if ambient is None else ambient)
        mesh = load_obj(path, material=chosen_material)
        mesh.position = vec3(position)
        mesh.scale = vec3(scale)
        mesh.rotation = vec3(rotation)
        return self.add(mesh, chosen_material)

    def light(
        self,
        direction: Vector3 | tuple[float, float, float] = (-0.4, -0.8, -0.6),
        color: tuple[int, int, int] = (255, 255, 255),
        intensity: float = 1.0,
    ) -> DirectionalLight:
        return self.scene.add_light(
            DirectionalLight(direction=vec3(direction), color=color, intensity=intensity)
        )

    def tick(self) -> float:
        self.delta = min(self.clock.tick(self.fps) / 1000.0, 0.05)
        self.time += self.delta
        self.frame_index += 1
        return self.delta

    def events(self) -> list[object]:
        events = self.pygame.event.get()
        for event in events:
            if event.type == self.pygame.QUIT:
                self.stop()
        return list(events)

    def keys(self) -> object:
        self._keys = self.pygame.key.get_pressed()
        return self._keys

    def key(self, name: str | int) -> bool:
        keys = self._keys if self._keys is not None else self.keys()
        key_code = name if isinstance(name, int) else key_code_from_name(self.pygame, name)
        return bool(keys[key_code])

    def move(self, target: SceneTarget, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> SceneTarget:
        if isinstance(target, AppObject):
            return target.move(x, y, z)
        target.position = Vector3(target.position.x + x, target.position.y + y, target.position.z + z)
        return target

    def rotate(self, target: SceneTarget, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> SceneTarget:
        if isinstance(target, AppObject):
            return target.rotate(x, y, z)
        target.rotation = Vector3(target.rotation.x + x, target.rotation.y + y, target.rotation.z + z)
        return target

    def set_position(self, target: SceneTarget, x: float, y: float, z: float) -> SceneTarget:
        if isinstance(target, AppObject):
            return target.set_position((x, y, z))
        target.position = Vector3(x, y, z)
        return target

    def set_rotation(self, target: SceneTarget, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> SceneTarget:
        if isinstance(target, AppObject):
            return target.set_rotation((x, y, z))
        target.rotation = Vector3(x, y, z)
        return target

    def set_scale(self, target: SceneTarget, x: float, y: float, z: float) -> SceneTarget:
        if isinstance(target, AppObject):
            return target.set_scale((x, y, z))
        target.scale = Vector3(x, y, z)
        return target

    def set_color(
        self,
        target: SceneTarget,
        color: tuple[int, int, int],
        ambient: float | None = None,
    ) -> SceneTarget:
        if isinstance(target, AppObject):
            return target.set_color(color, ambient)

        current = target.material or Material()
        self.scene.set_material(target, Material(color=color, ambient=current.ambient if ambient is None else ambient))
        return target

    def distance(self, first: SceneTarget | VectorLike, second: SceneTarget | VectorLike) -> float:
        return (_target_position(first) - _target_position(second)).length()

    def overlaps(
        self,
        first: SceneTarget | VectorLike,
        second: SceneTarget | VectorLike,
        padding: float = 0.0,
    ) -> bool:
        if isinstance(first, Vector3) or isinstance(first, tuple):
            if isinstance(second, Vector3) or isinstance(second, tuple):
                return self.distance(first, second) <= padding
            return _point_in_bounds(vec3(first), _target_bounds(second), padding)
        if isinstance(second, Vector3) or isinstance(second, tuple):
            return _point_in_bounds(vec3(second), _target_bounds(first), padding)
        return _bounds_overlap(_target_bounds(first), _target_bounds(second), padding)

    def draw_text(
        self,
        text: str,
        position: tuple[int, int] = (20, 20),
        color: tuple[int, int, int] = (240, 244, 255),
        size: int = 28,
        cache: bool = True,
    ) -> None:
        if cache:
            surface = self._text_surface(text, color, "consolas", size)
        else:
            surface = self._font("consolas", size).render(text, True, color)
        self.screen.blit(surface, position)

    def _font(self, name: str, size: int, bold: bool = False) -> object:
        key = (name, size, bold)
        font = self._font_cache.get(key)
        if font is None:
            font = self.pygame.font.SysFont(name, size, bold=bold)
            self._font_cache[key] = font
        return font

    def _text_surface(
        self,
        text: str,
        color: tuple[int, int, int],
        font_name: str,
        size: int,
        bold: bool = False,
    ) -> object:
        key = (text, color, font_name, size, bold)
        surface = self._text_cache.get(key)
        if surface is None:
            if len(self._text_cache) > 512:
                self._text_cache.clear()
            surface = self._font(font_name, size, bold).render(text, True, color)
            self._text_cache[key] = surface
        return surface

    def render(self) -> None:
        self.render_scene(self.scene)

    def render_scene(self, scene: Scene) -> None:
        self.renderer.render(scene, self.camera, self.render_surface, mode=self.mode)
        if self.render_surface is not self.screen:
            self.pygame.transform.scale(self.render_surface, self.size, self.screen)

    def flip(self) -> None:
        self.pygame.display.flip()

    def stop(self) -> None:
        self.running = False

    def run(
        self,
        update: UpdateCallback | None = None,
        on_event: EventCallback | None = None,
        overlay: OverlayCallback | None = None,
        close_on_escape: bool = True,
    ) -> None:
        while self.running:
            delta = self.tick()
            self._keys = None
            for event in self.events():
                if close_on_escape and event.type == self.pygame.KEYDOWN and event.key == self.pygame.K_ESCAPE:
                    self.stop()
                if on_event is not None:
                    on_event(event, self)

            if update is not None:
                update(self, delta)

            self.render()
            if overlay is not None:
                overlay(self)
            self.flip()


def vec3(value: Vector3 | tuple[float, float, float]) -> Vector3:
    if isinstance(value, Vector3):
        return value
    return Vector3(value[0], value[1], value[2])


def size3(value: SizeLike) -> Vector3:
    if isinstance(value, int | float):
        return Vector3(float(value), float(value), float(value))
    return vec3(value)


def make_material(
    material: Material | None,
    color: tuple[int, int, int] | None,
    ambient: float | None,
) -> Material | None:
    if material is not None:
        return material
    if color is None and ambient is None:
        return None
    default = Material()
    return Material(color=default.color if color is None else color, ambient=default.ambient if ambient is None else ambient)


def _target_meshes(target: SceneTarget) -> tuple[Mesh, ...]:
    if isinstance(target, AppObject):
        return target.meshes
    return (target,)


def _target_position(target: SceneTarget | VectorLike) -> Vector3:
    if isinstance(target, Vector3) or isinstance(target, tuple):
        return vec3(target)
    if isinstance(target, AppObject):
        return target.position
    return target.position


def _target_bounds(target: SceneTarget) -> tuple[Vector3, Vector3]:
    meshes = _target_meshes(target)
    min_bound, max_bound = _mesh_bounds(meshes[0])
    min_x, min_y, min_z = min_bound.x, min_bound.y, min_bound.z
    max_x, max_y, max_z = max_bound.x, max_bound.y, max_bound.z

    for mesh in meshes[1:]:
        mesh_min, mesh_max = _mesh_bounds(mesh)
        min_x = min(min_x, mesh_min.x)
        min_y = min(min_y, mesh_min.y)
        min_z = min(min_z, mesh_min.z)
        max_x = max(max_x, mesh_max.x)
        max_y = max(max_y, mesh_max.y)
        max_z = max(max_z, mesh_max.z)

    return Vector3(min_x, min_y, min_z), Vector3(max_x, max_y, max_z)


def _mesh_bounds(mesh: Mesh) -> tuple[Vector3, Vector3]:
    if not mesh.vertices:
        return mesh.position, mesh.position

    first = mesh.vertices[0]
    first_world = Vector3(
        mesh.position.x + first.x * mesh.scale.x,
        mesh.position.y + first.y * mesh.scale.y,
        mesh.position.z + first.z * mesh.scale.z,
    )
    min_x = max_x = first_world.x
    min_y = max_y = first_world.y
    min_z = max_z = first_world.z

    for vertex in mesh.vertices[1:]:
        world = Vector3(
            mesh.position.x + vertex.x * mesh.scale.x,
            mesh.position.y + vertex.y * mesh.scale.y,
            mesh.position.z + vertex.z * mesh.scale.z,
        )
        min_x = min(min_x, world.x)
        min_y = min(min_y, world.y)
        min_z = min(min_z, world.z)
        max_x = max(max_x, world.x)
        max_y = max(max_y, world.y)
        max_z = max(max_z, world.z)

    return Vector3(min_x, min_y, min_z), Vector3(max_x, max_y, max_z)


def _bounds_overlap(
    first: tuple[Vector3, Vector3],
    second: tuple[Vector3, Vector3],
    padding: float,
) -> bool:
    first_min, first_max = first
    second_min, second_max = second
    return (
        first_min.x - padding <= second_max.x
        and first_max.x + padding >= second_min.x
        and first_min.y - padding <= second_max.y
        and first_max.y + padding >= second_min.y
        and first_min.z - padding <= second_max.z
        and first_max.z + padding >= second_min.z
    )


def _point_in_bounds(point: Vector3, bounds: tuple[Vector3, Vector3], padding: float) -> bool:
    minimum, maximum = bounds
    return (
        minimum.x - padding <= point.x <= maximum.x + padding
        and minimum.y - padding <= point.y <= maximum.y + padding
        and minimum.z - padding <= point.z <= maximum.z + padding
    )


def key_code_from_name(pygame: object, name: str) -> int:
    normalized = name.lower().strip()
    aliases = {
        "esc": "escape",
        "return": "enter",
        "left_arrow": "left",
        "right_arrow": "right",
        "up_arrow": "up",
        "down_arrow": "down",
    }
    normalized = aliases.get(normalized, normalized)
    for attr in (f"K_{normalized}", f"K_{normalized.upper()}"):
        if hasattr(pygame, attr):
            return int(getattr(pygame, attr))
    raise KeyError(f"Unknown key name: {name}")
