"""A compact flat-shaded 3D tunnel game built with MiniPy3DR and pygame."""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minipy3dr import DirectionalLight, Material, Mesh, MiniPy3DRApp, Scene, Vector3


SCREEN_SIZE = (920, 640)
RENDER_SCALE = 0.62
PLAYER_Z = -4.6
SPAWN_Z = -34.0
REMOVE_Z = 1.2
BOUND_X = 3.0
BOUND_Y = 1.45
SEGMENT_SPACING = 3.2


@dataclass
class TunnelObject:
    x: float
    y: float
    z: float
    kind: str
    mesh: Mesh
    radius: float
    passed: bool = False


class LumenDriftGame:
    def __init__(self) -> None:
        self.app = MiniPy3DRApp(
            size=SCREEN_SIZE,
            title="MiniPy3DR - Lumen Drift 3D",
            render_scale=RENDER_SCALE,
            background=(7, 9, 15),
            fov=74,
            near=0.1,
            far=100,
        )
        self.pygame = self.app.pygame
        self.screen = self.app.screen
        self.camera = self.app.camera
        self.font = self.pygame.font.SysFont("consolas", 25)
        self.big_font = self.pygame.font.SysFont("consolas", 68, bold=True)

        self.light = DirectionalLight(direction=Vector3(-0.35, -0.75, -0.55), intensity=1.12)
        self.floor_material = Material((31, 38, 52), ambient=0.32)
        self.wall_material = Material((24, 30, 44), ambient=0.3)
        self.trim_material = Material((57, 92, 128), ambient=0.35)
        self.player_material = Material((70, 216, 255), ambient=0.2)
        self.wing_material = Material((54, 138, 220), ambient=0.24)
        self.hazard_material = Material((238, 76, 96), ambient=0.18)
        self.core_material = Material((255, 209, 82), ambient=0.26)
        self.shadow_material = Material((11, 14, 21), ambient=0.5)

        self.best_score = 0
        self.reset()

    def reset(self) -> None:
        self.player_x = 0.0
        self.player_y = 0.0
        self.velocity_x = 0.0
        self.velocity_y = 0.0
        self.objects: list[TunnelObject] = []
        self.score = 0.0
        self.combo = 0
        self.distance = 0.0
        self.spawn_timer = 0.45
        self.time = 0.0
        self.game_over = False

    def run(self) -> None:
        while self.app.running:
            delta = self.app.tick()
            self._handle_events()
            if not self.game_over:
                self._update(delta)
            self._render()

    def _handle_events(self) -> None:
        for event in self.app.events():
            if event.type != self.pygame.KEYDOWN:
                continue

            if event.key in (self.pygame.K_ESCAPE, self.pygame.K_q):
                self.app.stop()
            if event.key == self.pygame.K_SPACE and self.game_over:
                self.best_score = max(self.best_score, int(self.score))
                self.reset()

    def _update(self, delta: float) -> None:
        self.time += delta
        speed = self._speed()
        self.distance += speed * delta
        self.score += speed * delta * (4.0 + self.combo * 0.08)

        self._update_player(delta)
        self._update_camera()

        for obj in self.objects:
            obj.z += speed * delta
            obj.mesh.position = Vector3(obj.x, self._object_y(obj), obj.z)
            obj.mesh.rotation = self._object_rotation(obj, delta)

            if obj.kind == "hazard" and not obj.passed and obj.z > PLAYER_Z:
                obj.passed = True
                self.score += 20

        self._check_collisions()
        self.objects = [obj for obj in self.objects if obj.z < REMOVE_Z and obj.kind != "collected"]

        self.spawn_timer -= delta
        if self.spawn_timer <= 0:
            self._spawn_wave()
            pressure = min(0.34, self.distance * 0.0025)
            self.spawn_timer = max(0.52, random.uniform(0.9, 1.25) - pressure)

    def _update_player(self, delta: float) -> None:
        keys = self.app.keys()
        axis_x = int(keys[self.pygame.K_RIGHT] or keys[self.pygame.K_d]) - int(
            keys[self.pygame.K_LEFT] or keys[self.pygame.K_a]
        )
        axis_y = int(keys[self.pygame.K_UP] or keys[self.pygame.K_w]) - int(
            keys[self.pygame.K_DOWN] or keys[self.pygame.K_s]
        )

        self.velocity_x += axis_x * 18.0 * delta
        self.velocity_y += axis_y * 14.0 * delta
        damping = max(0.0, 1.0 - 7.5 * delta)
        self.velocity_x *= damping
        self.velocity_y *= damping

        self.player_x = _clamp(self.player_x + self.velocity_x * delta, -BOUND_X, BOUND_X)
        self.player_y = _clamp(self.player_y + self.velocity_y * delta, -BOUND_Y, BOUND_Y)

        if abs(self.player_x) >= BOUND_X:
            self.velocity_x *= -0.15
        if abs(self.player_y) >= BOUND_Y:
            self.velocity_y *= -0.15

    def _update_camera(self) -> None:
        self.camera.position = Vector3(self.player_x * 0.12, 0.32 + self.player_y * 0.08, 0.72)
        self.camera.look_at(Vector3(self.player_x * 0.22, self.player_y * 0.16, -12.0))

    def _spawn_wave(self) -> None:
        slots = [(x, y) for x in (-2.4, 0.0, 2.4) for y in (-1.0, 1.0)]
        gap = random.choice(slots)
        wave_z = SPAWN_Z

        for x, y in slots:
            if (x, y) == gap or random.random() < 0.18:
                continue
            size = random.uniform(0.66, 0.86)
            mesh = self._cube(Vector3(x, y, wave_z), Vector3(size, size, size))
            self.objects.append(TunnelObject(x, y, wave_z, "hazard", mesh, radius=size * 0.7))

        if random.random() < 0.78:
            x, y = gap
            mesh = self._cube(Vector3(x, y, wave_z - 0.9), Vector3(0.42, 0.42, 0.42))
            self.objects.append(TunnelObject(x, y, wave_z - 0.9, "core", mesh, radius=0.42))

    def _check_collisions(self) -> None:
        for obj in self.objects:
            if abs(obj.z - PLAYER_Z) > 0.85:
                continue

            dx = obj.x - self.player_x
            dy = self._object_y(obj) - self.player_y
            hit_distance = obj.radius + 0.46
            if dx * dx + dy * dy > hit_distance * hit_distance:
                continue

            if obj.kind == "core":
                self.score += 120 + self.combo * 18
                self.combo += 1
                obj.kind = "collected"
                continue

            self.game_over = True
            self.best_score = max(self.best_score, int(self.score))

    def _render(self) -> None:
        scene = Scene()
        scene.add_light(self.light)
        self._add_tunnel(scene)
        self._add_player(scene)

        for obj in self.objects:
            if obj.kind == "collected":
                continue
            material = self.core_material if obj.kind == "core" else self.hazard_material
            scene.add(obj.mesh, material)

        self.app.render_scene(scene)
        self._draw_hud()
        self.app.flip()

    def _add_tunnel(self, scene: Scene) -> None:
        segment_offset = self.distance % SEGMENT_SPACING
        for index in range(11):
            z = -3.0 - index * SEGMENT_SPACING + segment_offset
            scene.add(self._cube(Vector3(0, -2.05, z), Vector3(7.7, 0.09, 1.18)), self.floor_material)
            scene.add(self._cube(Vector3(0, 2.05, z), Vector3(7.7, 0.09, 1.18)), self.wall_material)
            scene.add(self._cube(Vector3(-3.85, 0, z), Vector3(0.1, 4.0, 1.18)), self.wall_material)
            scene.add(self._cube(Vector3(3.85, 0, z), Vector3(0.1, 4.0, 1.18)), self.wall_material)

            if index % 2 == 0:
                scene.add(self._cube(Vector3(-2.55, -1.96, z), Vector3(0.18, 0.08, 1.1)), self.trim_material)
                scene.add(self._cube(Vector3(2.55, -1.96, z), Vector3(0.18, 0.08, 1.1)), self.trim_material)

        scene.add(self._cube(Vector3(self.player_x, -1.82, PLAYER_Z), Vector3(0.82, 0.04, 0.82)), self.shadow_material)

    def _add_player(self, scene: Scene) -> None:
        bank = _clamp(-self.velocity_x * 0.04, -0.34, 0.34)
        bob = math.sin(self.time * 9.0) * 0.035
        base = Vector3(self.player_x, self.player_y + bob, PLAYER_Z)

        body = self._cube(base, Vector3(0.58, 0.36, 0.76), Vector3(0.0, bank, bank * 0.8))
        left_wing = self._cube(
            Vector3(base.x - 0.62, base.y - 0.04, base.z + 0.08),
            Vector3(0.66, 0.12, 0.36),
            Vector3(0.0, bank, bank * 0.8),
        )
        right_wing = self._cube(
            Vector3(base.x + 0.62, base.y - 0.04, base.z + 0.08),
            Vector3(0.66, 0.12, 0.36),
            Vector3(0.0, bank, bank * 0.8),
        )
        scene.add(body, self.player_material)
        scene.add(left_wing, self.wing_material)
        scene.add(right_wing, self.wing_material)

    def _draw_hud(self) -> None:
        score = int(self.score)
        score_text = self.font.render(f"SCORE {score:05d}", True, (232, 242, 255))
        combo_text = self.font.render(f"COMBO {self.combo:02d}", True, (255, 214, 116))
        best_text = self.font.render(f"BEST {self.best_score:05d}", True, (142, 164, 194))
        speed_text = self.font.render(f"SPEED {self._speed():04.1f}", True, (132, 224, 255))

        self.screen.blit(score_text, (24, 18))
        self.screen.blit(combo_text, (24, 48))
        self.screen.blit(speed_text, (24, 78))
        self.screen.blit(best_text, (SCREEN_SIZE[0] - best_text.get_width() - 24, 18))

        if self.game_over:
            title = self.big_font.render("DRIFT LOST", True, (255, 234, 220))
            rect = title.get_rect(center=(SCREEN_SIZE[0] // 2, SCREEN_SIZE[1] // 2 - 8))
            self.screen.blit(title, rect)

    def _object_y(self, obj: TunnelObject) -> float:
        if obj.kind == "core":
            return obj.y + math.sin(self.time * 5.5 + obj.x) * 0.12
        return obj.y

    def _object_rotation(self, obj: TunnelObject, delta: float) -> Vector3:
        if obj.kind == "core":
            return Vector3(
                obj.mesh.rotation.x + delta * 3.8,
                obj.mesh.rotation.y + delta * 4.8,
                obj.mesh.rotation.z + delta * 2.4,
            )
        return Vector3(obj.mesh.rotation.x + delta * 0.65, obj.mesh.rotation.y + delta * 0.4, 0.0)

    def _speed(self) -> float:
        return 8.0 + min(8.5, self.distance * 0.025 + self.combo * 0.12)

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


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def main() -> None:
    LumenDriftGame().run()


if __name__ == "__main__":
    main()
