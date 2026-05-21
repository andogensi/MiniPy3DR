"""High-level pygame app wrapper for MiniPy3DR."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from minipy3dr.core import DirectionalLight, Material, Mesh, PerspectiveCamera, Scene
from minipy3dr.math import Vector3
from minipy3dr.render import Renderer


UpdateCallback = Callable[["MiniPy3DRApp", float], None]
EventCallback = Callable[[object, "MiniPy3DRApp"], None]
OverlayCallback = Callable[["MiniPy3DRApp"], None]


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
        mode: str = "solid_numpy",
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
        self.mode = mode
        self.fps = fps
        self.screen = pygame.display.set_mode(size)
        self.render_surface = (
            self.screen if self.render_size == size else pygame.Surface(self.render_size)
        )
        pygame.display.set_caption(title)
        self.clock = pygame.time.Clock()
        self.renderer = Renderer(self.render_size, background=background)
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

    @property
    def frame(self) -> AppFrame:
        return AppFrame(self.delta, self.time, self.frame_index)

    def add(self, mesh: Mesh, material: Material | None = None) -> Mesh:
        return self.scene.add(mesh, material)

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
        return self.pygame.key.get_pressed()

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
