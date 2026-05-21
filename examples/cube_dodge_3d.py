"""A small 3D lane-dodging game built with the current MiniPy3DR renderer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pygame

from minipy3dr import Material, Mesh, PerspectiveCamera, Renderer, Scene
from minipy3dr.math import Vector3


SCREEN_SIZE = (900, 640)
RENDER_SCALE = 1.0
RENDER_SIZE = (int(SCREEN_SIZE[0] * RENDER_SCALE), int(SCREEN_SIZE[1] * RENDER_SCALE))
LANES = (-2.1, 0.0, 2.1)
PLAYER_Z = -4.6
SPAWN_Z = -34.0


@dataclass
class RunnerObject:
    lane: int
    z: float
    kind: str
    mesh: Mesh
    passed: bool = False


class CubeDodgeGame:
    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode(SCREEN_SIZE)
        self.render_surface = self.screen if RENDER_SIZE == SCREEN_SIZE else pygame.Surface(RENDER_SIZE)
        pygame.display.set_caption("MiniPy3DR - Cube Dodge 3D")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 26)
        self.big_font = pygame.font.SysFont("consolas", 64, bold=True)

        self.renderer = Renderer(RENDER_SIZE, background=(10, 13, 20))
        self.camera = PerspectiveCamera(
            fov=68,
            aspect=RENDER_SIZE[0] / RENDER_SIZE[1],
            near=0.1,
            far=120,
        )

        self.road_material = Material((36, 42, 54))
        self.line_material = Material((90, 104, 128))
        self.player_material = Material((80, 210, 255))
        self.obstacle_material = Material((238, 76, 92))
        self.bonus_material = Material((255, 202, 74))
        self.shadow_material = Material((18, 20, 28))

        self.best_score = 0
        self.track_color_cache = None
        self.track_depth_cache = None
        self.reset()

    def reset(self) -> None:
        self.player_lane = 1
        self.player_x = LANES[self.player_lane]
        self.objects: list[RunnerObject] = []
        self.score = 0
        self.combo = 0
        self.spawn_timer = 0.3
        self.time = 0.0
        self.game_over = False

    def run(self) -> None:
        while True:
            delta = min(self.clock.tick(60) / 1000.0, 0.05)
            self._handle_events()
            if not self.game_over:
                self._update(delta)
            self._render()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if event.type != pygame.KEYDOWN:
                continue

            if event.key in (pygame.K_ESCAPE, pygame.K_q):
                raise SystemExit
            if event.key in (pygame.K_LEFT, pygame.K_a):
                self.player_lane = max(0, self.player_lane - 1)
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self.player_lane = min(len(LANES) - 1, self.player_lane + 1)
            elif event.key == pygame.K_SPACE and self.game_over:
                self.reset()

    def _update(self, delta: float) -> None:
        self.time += delta
        target_x = LANES[self.player_lane]
        self.player_x += (target_x - self.player_x) * min(1.0, delta * 14.0)

        speed = 7.0 + min(9.0, self.score * 0.12 + self.time * 0.08)
        for obj in self.objects:
            obj.z += speed * delta
            obj.mesh.position = Vector3(LANES[obj.lane], self._object_y(obj), obj.z)
            obj.mesh.rotation = self._object_rotation(obj, delta)

            if obj.kind == "obstacle" and not obj.passed and obj.z > PLAYER_Z:
                obj.passed = True
                self.score += 1
                self.combo += 1

        self._check_collisions()
        self.objects = [obj for obj in self.objects if obj.z < -0.6 and obj.kind != "collected"]

        self.spawn_timer -= delta
        if self.spawn_timer <= 0:
            self._spawn_object()
            pressure = min(0.6, self.score * 0.008)
            self.spawn_timer = max(0.32, random.uniform(0.58, 1.05) - pressure)

    def _spawn_object(self) -> None:
        lane = random.randrange(len(LANES))
        if random.random() < 0.18:
            mesh = self._cube(
                position=Vector3(LANES[lane], -1.06, SPAWN_Z),
                scale=Vector3(0.46, 0.46, 0.46),
            )
            self.objects.append(RunnerObject(lane, SPAWN_Z, "bonus", mesh))
            return

        mesh = self._cube(
            position=Vector3(LANES[lane], -1.0, SPAWN_Z),
            scale=Vector3(0.95, 0.95, 0.95),
        )
        self.objects.append(RunnerObject(lane, SPAWN_Z, "obstacle", mesh))

    def _check_collisions(self) -> None:
        for obj in self.objects:
            if abs(obj.z - PLAYER_Z) > 0.75:
                continue
            if abs(LANES[obj.lane] - self.player_x) > 0.58:
                continue

            if obj.kind == "bonus":
                self.score += 5 + min(self.combo, 5)
                self.combo += 1
                obj.kind = "collected"
                continue

            self.game_over = True
            self.best_score = max(self.best_score, self.score)

    def _render(self) -> None:
        actor_scene = Scene()
        self._ensure_track_cache()

        player = self._cube(
            position=Vector3(self.player_x, -1.08, PLAYER_Z),
            rotation=Vector3(self.time * 1.8, self.time * 2.4, 0.2),
            scale=Vector3(0.7, 0.7, 0.7),
        )
        actor_scene.add(player, self.player_material)

        for obj in self.objects:
            if obj.kind == "collected":
                continue
            material = self.bonus_material if obj.kind == "bonus" else self.obstacle_material
            actor_scene.add(obj.mesh, material)

        self.renderer.numpy_buffer.color[:, :] = self.track_color_cache
        self.renderer.numpy_buffer.depth[:, :] = self.track_depth_cache
        self.renderer.draw_solid_numpy_scene(actor_scene, self.camera)
        self.renderer.blit_numpy_buffer(self.render_surface)
        if self.render_surface is not self.screen:
            pygame.transform.scale(self.render_surface, SCREEN_SIZE, self.screen)
        self._draw_hud()
        pygame.display.flip()

    def _ensure_track_cache(self) -> None:
        if self.track_color_cache is not None and self.track_depth_cache is not None:
            return

        track_scene = Scene()
        self._add_track(track_scene)
        self.renderer.clear_numpy_buffer()
        self.renderer.draw_solid_numpy_scene(track_scene, self.camera)
        self.track_color_cache = self.renderer.numpy_buffer.color.copy()
        self.track_depth_cache = self.renderer.numpy_buffer.depth.copy()

    def _add_track(self, scene: Scene) -> None:
        road = self._cube(
            position=Vector3(0.0, -1.62, -18.0),
            scale=Vector3(7.2, 0.1, 34.0),
        )
        scene.add(road, self.road_material)

        for x in (-1.05, 1.05):
            marker = self._cube(
                position=Vector3(x, -1.52, -18.0),
                scale=Vector3(0.06, 0.06, 34.0),
            )
            scene.add(marker, self.line_material)

        for lane_x in LANES:
            shadow = self._cube(
                position=Vector3(lane_x, -1.50, PLAYER_Z),
                scale=Vector3(0.95, 0.05, 0.95),
            )
            scene.add(shadow, self.shadow_material)

    def _draw_hud(self) -> None:
        score_text = self.font.render(f"SCORE {self.score:04d}", True, (235, 242, 255))
        best_text = self.font.render(f"BEST {self.best_score:04d}", True, (148, 164, 190))
        self.screen.blit(score_text, (24, 20))
        self.screen.blit(best_text, (SCREEN_SIZE[0] - best_text.get_width() - 24, 20))

        if self.game_over:
            title = self.big_font.render("GAME OVER", True, (255, 238, 220))
            rect = title.get_rect(center=(SCREEN_SIZE[0] // 2, SCREEN_SIZE[1] // 2 - 20))
            self.screen.blit(title, rect)

    def _cube(
        self,
        position: Vector3,
        scale: Vector3,
        rotation: Vector3 | None = None,
    ) -> Mesh:
        mesh = Mesh.cube(size=1.0)
        mesh.position = position
        mesh.scale = scale
        mesh.rotation = rotation or Vector3()
        return mesh

    def _object_y(self, obj: RunnerObject) -> float:
        if obj.kind == "bonus":
            return -1.06 + 0.18 * abs((self.time * 2.5) % 2.0 - 1.0)
        return -1.0

    def _object_rotation(self, obj: RunnerObject, delta: float) -> Vector3:
        if obj.kind == "bonus":
            return Vector3(
                obj.mesh.rotation.x + delta * 2.8,
                obj.mesh.rotation.y + delta * 3.6,
                obj.mesh.rotation.z + delta * 1.8,
            )
        return Vector3(obj.mesh.rotation.x + delta * 0.8, obj.mesh.rotation.y + delta * 0.5, 0.0)


def main() -> None:
    CubeDodgeGame().run()


if __name__ == "__main__":
    main()
