"""Maze Delivery Action: a small class-based MiniPy3DR game.

Run from the repository root:

    python examples/maze_delivery_action.py
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import os
import sys

# Some school PCs run files from unpredictable working directories.
os.chdir(os.path.dirname(os.path.abspath(__file__)))

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minipy3dr import App, Mesh, Vector3


TILE = 1.25
FLOOR_Y = -0.08
PLAYER_SPEED = 3.2
GUARD_SPEED = 1.35
PLAYER_RADIUS = 0.42
TIME_LIMIT = 75.0

MAP_DATA = [
    "###############",
    "#S....#....G..#",
    "#.##..#..##...#",
    "#....C.......E#",
    "#.##.###.##...#",
    "#P...#...E....#",
    "#.##.#.####...#",
    "#....#.......E#",
    "#.######.##...#",
    "#..E....C....E#",
    "###############",
]


@dataclass
class MovingActor:
    """Meshes that move together as one visible character."""

    body: Mesh
    head: Mesh

    def set_position(self, x: float, z: float) -> None:
        """Place the actor on the maze floor."""

        self.body.position = Vector3(x, 0.36, z)
        self.head.position = Vector3(x, 0.92, z)

    @property
    def x(self) -> float:
        return self.body.position.x

    @property
    def z(self) -> float:
        return self.body.position.z


class Maze:
    """Grid map, collision checks, and static 3D maze meshes."""

    def __init__(self, rows: list[str]) -> None:
        self.rows = rows
        self.height = len(rows)
        self.width = len(rows[0])

    def cell_center(self, row: int, col: int) -> tuple[float, float]:
        """Convert a map cell into world x/z coordinates."""

        x = (col - (self.width - 1) / 2) * TILE
        z = (row - (self.height - 1) / 2) * TILE
        return x, z

    def world_cell(self, x: float, z: float) -> tuple[int, int]:
        """Convert world x/z coordinates back into a map cell."""

        col = math.floor(x / TILE + self.width / 2)
        row = math.floor(z / TILE + self.height / 2)
        return row, col

    def find(self, marker: str) -> tuple[int, int]:
        """Return the first map cell containing marker."""

        for row, line in enumerate(self.rows):
            col = line.find(marker)
            if col != -1:
                return row, col
        raise ValueError(f"marker not found: {marker}")

    def find_all(self, marker: str) -> list[tuple[int, int]]:
        """Return all map cells containing marker."""

        cells: list[tuple[int, int]] = []
        for row, line in enumerate(self.rows):
            for col, value in enumerate(line):
                if value == marker:
                    cells.append((row, col))
        return cells

    def is_wall_cell(self, row: int, col: int) -> bool:
        if row < 0 or col < 0 or row >= self.height or col >= self.width:
            return True
        return self.rows[row][col] == "#"

    def is_blocked(self, x: float, z: float, radius: float = PLAYER_RADIUS) -> bool:
        """Check four corners so actors do not slide through walls."""

        for ox in (-radius, radius):
            for oz in (-radius, radius):
                row, col = self.world_cell(x + ox, z + oz)
                if self.is_wall_cell(row, col):
                    return True
        return False

    def build(self, app: App) -> None:
        """Create floor, walls, package marker, and goal marker."""

        for row, line in enumerate(self.rows):
            for col, value in enumerate(line):
                x, z = self.cell_center(row, col)
                if value == "#":
                    color = (88, 92, 104) if (row + col) % 2 else (104, 96, 86)
                    app.box(
                        position=(x, 0.55, z),
                        size=(TILE, 1.2, TILE),
                        color=color,
                        ambient=0.3,
                    )
                else:
                    floor_color = (34, 42, 48) if (row + col) % 2 else (39, 47, 42)
                    app.box(
                        position=(x, FLOOR_Y, z),
                        size=(TILE * 0.96, 0.08, TILE * 0.96),
                        color=floor_color,
                        ambient=0.55,
                    )


class Player:
    """The delivery person controlled by the keyboard."""

    def __init__(self, app: App, start: tuple[float, float]) -> None:
        body = app.box(size=(0.56, 0.72, 0.56), color=(72, 190, 235), ambient=0.38)
        head = app.box(size=(0.42, 0.34, 0.42), color=(245, 207, 150), ambient=0.45)
        parcel = app.box(size=(0.46, 0.22, 0.46), color=(194, 132, 62), ambient=0.48)
        self.actor = MovingActor(body, head)
        self.parcel_mesh = parcel
        self.has_package = False
        self.spawn = start
        self.invincible = 0.0
        self.set_position(*start)

    def set_position(self, x: float, z: float) -> None:
        self.actor.set_position(x, z)
        self._update_parcel_mesh()

    def reset(self) -> None:
        self.has_package = False
        self.invincible = 1.0
        self.set_position(*self.spawn)

    def update(self, app: App, maze: Maze, delta: float) -> None:
        """Read keys, move with wall collision, and animate the player."""

        dx = dz = 0.0
        if app.key("left") or app.key("a"):
            dx -= PLAYER_SPEED * delta
        if app.key("right") or app.key("d"):
            dx += PLAYER_SPEED * delta
        if app.key("up") or app.key("w"):
            dz -= PLAYER_SPEED * delta
        if app.key("down") or app.key("s"):
            dz += PLAYER_SPEED * delta

        x, z = self.actor.x, self.actor.z
        if not maze.is_blocked(x + dx, z):
            x += dx
        if not maze.is_blocked(x, z + dz):
            z += dz
        self.set_position(x, z)

        self.invincible = max(0.0, self.invincible - delta)
        spin = delta * (5.0 if dx or dz else 1.8)
        app.rotate(self.actor.body, y=spin)
        self._update_parcel_mesh()

    def _update_parcel_mesh(self) -> None:
        self.parcel_mesh.visible = self.has_package
        self.parcel_mesh.position = Vector3(self.actor.x, 1.2, self.actor.z)


class Package:
    """A parcel that can be picked up once."""

    def __init__(self, app: App, position: tuple[float, float]) -> None:
        self.position = position
        self.mesh = app.box(
            position=(position[0], 0.28, position[1]),
            size=(0.62, 0.46, 0.62),
            color=(206, 140, 60),
            ambient=0.48,
        )

    def update(self, app: App, delta: float, visible: bool) -> None:
        self.mesh.visible = visible
        if visible:
            app.rotate(self.mesh, y=delta * 1.6)


class Guard:
    """A simple patrol enemy that reverses direction at walls."""

    def __init__(self, app: App, position: tuple[float, float], horizontal: bool) -> None:
        body = app.box(size=(0.58, 0.72, 0.58), color=(220, 70, 76), ambient=0.34)
        head = app.box(size=(0.42, 0.32, 0.42), color=(255, 104, 96), ambient=0.4)
        self.actor = MovingActor(body, head)
        self.direction = Vector3(1.0 if horizontal else 0.0, 0.0, 0.0 if horizontal else 1.0)
        self.actor.set_position(*position)

    def update(self, app: App, maze: Maze, delta: float) -> None:
        dx = self.direction.x * GUARD_SPEED * delta
        dz = self.direction.z * GUARD_SPEED * delta
        next_x = self.actor.x + dx
        next_z = self.actor.z + dz
        if maze.is_blocked(next_x, next_z, radius=0.38):
            self.direction = Vector3(-self.direction.x, 0.0, -self.direction.z)
            return
        self.actor.set_position(next_x, next_z)
        app.rotate(self.actor.head, y=delta * 3.2)


class BonusToken:
    """Optional mail tokens that increase score but are not required."""

    def __init__(self, app: App, position: tuple[float, float]) -> None:
        self.mesh = app.box(
            position=(position[0], 0.32, position[1]),
            size=(0.38, 0.38, 0.38),
            color=(255, 216, 70),
            ambient=0.65,
        )
        self.collected = False

    def update(self, app: App, delta: float) -> None:
        if not self.collected:
            app.rotate(self.mesh, x=delta * 1.5, y=delta * 3.0)


class DeliveryGame:
    """Main game rules: pickup, delivery, scoring, lives, and HUD."""

    def __init__(self) -> None:
        self.app = App(
            size=(900, 620),
            title="Maze Delivery Action",
            render_scale=1.15,
            background=(13, 16, 21),
            mode="native",
            fov=58,
            far=80,
        )
        self.maze = Maze(MAP_DATA)
        self.score = 0
        self.lives = 3
        self.time_left = TIME_LIMIT
        self.state = "playing"

        self.app.light(direction=(-0.4, -0.85, -0.35), color=(255, 244, 220), intensity=1.0)
        self.app.light(direction=(0.75, -0.35, 0.25), color=(110, 170, 255), intensity=0.25)
        self.maze.build(self.app)

        start = self.maze.cell_center(*self.maze.find("S"))
        package = self.maze.cell_center(*self.maze.find("P"))
        goal = self.maze.cell_center(*self.maze.find("G"))
        self.player = Player(self.app, start)
        self.package = Package(self.app, package)
        self.goal = self.app.box(
            position=(goal[0], 0.12, goal[1]),
            size=(0.9, 0.24, 0.9),
            color=(78, 218, 120),
            ambient=0.68,
        )
        self.goal_position = goal
        self.tokens = [
            BonusToken(self.app, self.maze.cell_center(row, col))
            for row, col in self.maze.find_all("C")
        ]
        self.guards = [
            Guard(self.app, self.maze.cell_center(row, col), horizontal=index % 2 == 0)
            for index, (row, col) in enumerate(self.maze.find_all("E"))
        ]

        self.app.camera.position = Vector3(0.0, 11.0, 9.5)
        self.app.camera.look_at(Vector3(0.0, 0.0, 0.0))

    def run(self) -> None:
        self.app.run(update=self.update, on_event=self.on_event, overlay=self.overlay)

    def on_event(self, event: object, app: App) -> None:
        if event.type == app.pygame.KEYDOWN and event.key == app.pygame.K_r:
            self.restart()

    def restart(self) -> None:
        self.score = 0
        self.lives = 3
        self.time_left = TIME_LIMIT
        self.state = "playing"
        self.player.reset()
        self.package.mesh.visible = True
        for token in self.tokens:
            token.collected = False
            token.mesh.visible = True

    def update(self, app: App, delta: float) -> None:
        self.package.update(app, delta, visible=not self.player.has_package)
        for token in self.tokens:
            token.update(app, delta)

        if self.state != "playing":
            app.rotate(self.goal, y=delta * 1.8)
            return

        self.time_left = max(0.0, self.time_left - delta)
        if self.time_left <= 0:
            self.state = "lost"
            return

        self.player.update(app, self.maze, delta)
        for guard in self.guards:
            guard.update(app, self.maze, delta)
        app.rotate(self.goal, y=delta * 1.8)

        self.check_pickups()
        self.check_guard_hits()
        self.check_goal()

    def check_pickups(self) -> None:
        if not self.player.has_package and self.distance_to_player(self.package.position) < 0.72:
            self.player.has_package = True
            self.score += 50

        for token in self.tokens:
            if token.collected or self.distance_to_player((token.mesh.position.x, token.mesh.position.z)) >= 0.64:
                continue
            token.collected = True
            token.mesh.visible = False
            self.score += 25

    def check_guard_hits(self) -> None:
        if self.player.invincible > 0:
            return
        for guard in self.guards:
            if self.distance_to_player((guard.actor.x, guard.actor.z)) < 0.78:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = "lost"
                else:
                    self.player.reset()
                return

    def check_goal(self) -> None:
        if self.player.has_package and self.distance_to_player(self.goal_position) < 0.72:
            self.score += int(self.time_left) * 3 + self.lives * 80
            self.player.has_package = False
            self.state = "won"

    def distance_to_player(self, point: tuple[float, float]) -> float:
        dx = self.player.actor.x - point[0]
        dz = self.player.actor.z - point[1]
        return math.sqrt(dx * dx + dz * dz)

    def overlay(self, app: App) -> None:
        pygame = app.pygame
        draw = pygame.draw
        draw.rect(app.screen, (10, 12, 16), (14, 14, 304, 100), border_radius=5)
        app.draw_text(f"SCORE {self.score:04d}", (24, 22), size=24)
        app.draw_text(f"TIME {self.time_left:05.1f}", (24, 50), color=(230, 220, 150), size=24)
        app.draw_text(f"LIVES {self.lives}  PACKAGE {'YES' if self.player.has_package else 'NO'}", (24, 78), size=22)
        app.draw_text("WASD/ARROWS move   R restart   ESC quit", (22, app.size[1] - 34), color=(160, 172, 188), size=20)

        if self.state == "won":
            self.draw_centered("DELIVERY COMPLETE", 270, (94, 235, 135))
            self.draw_centered("Press R to play again", 314, (226, 232, 238), size=25)
        elif self.state == "lost":
            self.draw_centered("DELIVERY FAILED", 270, (240, 84, 84))
            self.draw_centered("Press R to try again", 314, (226, 232, 238), size=25)

    def draw_centered(self, text: str, y: int, color: tuple[int, int, int], size: int = 34) -> None:
        font = self.app.pygame.font.SysFont("consolas", size, bold=True)
        surface = font.render(text, True, color)
        rect = surface.get_rect(center=(self.app.size[0] // 2, y))
        self.app.screen.blit(surface, rect)


if __name__ == "__main__":
    DeliveryGame().run()
