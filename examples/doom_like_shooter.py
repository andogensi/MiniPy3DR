"""One-file DOOM-like shooter built with MiniPy3DR.

Run from the repository root:

    python examples/doom_like_shooter.py
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minipy3dr import App, Mesh, Vector3


TILE = 2.0
WALL_HEIGHT = 2.4
FLOOR_Y = -0.8
CEILING_Y = 1.75
EYE_Y = 0.45
PLAYER_RADIUS = 0.42
BULLET_SPEED = 24.0
ENEMY_BULLET_SPEED = 7.4
WALK_SPEED = 4.7
SPRINT_SPEED = 6.1
GROUND_ACCEL = 34.0
AIR_ACCEL = 13.5
GROUND_FRICTION = 28.0
AIR_DRAG = 0.55
JUMP_VELOCITY = 4.85
GRAVITY = 13.0
COYOTE_TIME = 0.11
JUMP_BUFFER_TIME = 0.11
STEP_HEIGHT = 0.2
LOW_COVER_HEIGHT = 0.64
RAISED_PLATFORM_HEIGHT = 0.98
MAX_HEALTH = 100
MAX_AMMO = 70
EXPLOSION_RADIUS = 3.2
BASE_PITCH = -0.035
MOUSE_SENSITIVITY = 0.003
MOUSE_PITCH_MIN = -0.42
MOUSE_PITCH_MAX = 0.36

MAP = [
    "######################",
    "#P.A..C....#....T....#",
    "#.##.####.#.##.###...#",
    "#..C....#.#....C.E...#",
    "#.##.##.#.#.####.#...#",
    "#....E#...#..B....H..#",
    "####.###.#.###.####..#",
    "#..B...#...RRT..#....#",
    "#.####.#.##RR##.#....#",
    "#....#.#...R...#..A..#",
    "#.##.#.#####.#.####..#",
    "#..H...C..E..#...T...#",
    "#.###.######.#.###...#",
    "#...B....A...#..E....#",
    "#.####.###.###.##.#..#",
    "#...C.....B....H.....#",
    "######################",
]

MAP_H = len(MAP)
MAP_W = len(MAP[0])
ORIGIN_X = -((MAP_W - 1) * TILE) / 2.0


@dataclass
class Bullet:
    mesh: Mesh
    velocity: Vector3
    ttl: float


@dataclass
class EnemyShot:
    mesh: Mesh
    velocity: Vector3
    ttl: float


@dataclass
class Particle:
    mesh: Mesh
    velocity: Vector3
    ttl: float
    life: float
    size: float


@dataclass
class Pickup:
    mesh: Mesh
    kind: str
    amount: int
    phase: float


@dataclass
class Barrel:
    body: Mesh
    band: Mesh
    exploded: bool = False


@dataclass
class LowCover:
    body: Mesh
    trim: Mesh
    height: float
    radius: float


@dataclass
class Enemy:
    body: Mesh
    head: Mesh
    eye_left: Mesh
    eye_right: Mesh
    hp: int = 4
    attack_timer: float = 0.0
    hurt_flash: float = 0.0
    bob_phase: float = 0.0
    floor_offset: float = 0.0
    stationary: bool = False


def cell_center(row: int, col: int) -> tuple[float, float]:
    return ORIGIN_X + col * TILE, -row * TILE


def world_cell(x: float, z: float) -> tuple[int, int]:
    col = math.floor((x - ORIGIN_X + TILE * 0.5) / TILE)
    row = math.floor((-z + TILE * 0.5) / TILE)
    return row, col


def is_wall_cell(row: int, col: int) -> bool:
    if row < 0 or col < 0 or row >= MAP_H or col >= MAP_W:
        return True
    return MAP[row][col] == "#"


def is_blocked(x: float, z: float, radius: float = PLAYER_RADIUS) -> bool:
    for ox in (-radius, radius):
        for oz in (-radius, radius):
            row, col = world_cell(x + ox, z + oz)
            if is_wall_cell(row, col):
                return True
    return False


def has_line_of_sight(start_x: float, start_z: float, end_x: float, end_z: float) -> bool:
    dx = end_x - start_x
    dz = end_z - start_z
    distance = math.sqrt(dx * dx + dz * dz)
    steps = max(1, int(distance / 0.28))
    for step in range(1, steps):
        t = step / steps
        row, col = world_cell(start_x + dx * t, start_z + dz * t)
        if is_wall_cell(row, col):
            return False
    return True


def xz_forward(yaw: float) -> tuple[float, float]:
    return -math.sin(yaw), -math.cos(yaw)


def xz_right(yaw: float) -> tuple[float, float]:
    return math.cos(yaw), -math.sin(yaw)


def distance_sq_xz(a: Vector3, b: Vector3) -> float:
    dx = a.x - b.x
    dz = a.z - b.z
    return dx * dx + dz * dz


def distance_sq_3d(a: Vector3, b: Vector3) -> float:
    dx = a.x - b.x
    dy = a.y - b.y
    dz = a.z - b.z
    return dx * dx + dy * dy + dz * dz


def approach(current: float, target: float, max_delta: float) -> float:
    if current < target:
        return min(target, current + max_delta)
    return max(target, current - max_delta)


def horizontal_speed() -> float:
    return math.sqrt(player_vel_x * player_vel_x + player_vel_z * player_vel_z)


def cover_overlaps(cover: LowCover, x: float, z: float, radius: float) -> bool:
    pos = cover.body.position
    dx = pos.x - x
    dz = pos.z - z
    return dx * dx + dz * dz < (radius + cover.radius) ** 2


def support_height_at(x: float, z: float, radius: float = PLAYER_RADIUS) -> float:
    height = 0.0
    for cover in covers:
        if cover_overlaps(cover, x, z, radius):
            height = max(height, cover.height)
    return height


def hits_low_cover(x: float, z: float, radius: float, y_offset: float) -> bool:
    for cover in covers:
        if cover_overlaps(cover, x, z, radius) and y_offset + STEP_HEIGHT < cover.height:
            return True
    return False


def is_player_blocked(x: float, z: float, y_offset: float, radius: float = PLAYER_RADIUS) -> bool:
    return (
        is_blocked(x, z, radius)
        or hits_barrel(x, z, radius)
        or hits_low_cover(x, z, radius, y_offset)
    )


def projectile_hits_world(pos: Vector3, radius: float = 0.08) -> bool:
    if pos.y <= FLOOR_Y + radius or pos.y >= CEILING_Y + radius:
        return True
    if is_blocked(pos.x, pos.z, radius):
        return True
    for cover in covers:
        if cover_overlaps(cover, pos.x, pos.z, radius) and pos.y <= FLOOR_Y + cover.height + radius:
            return True
    return False


app = App(
    size=(960, 600),
    title="Mini DOOM-like Shooter",
    render_scale=0.6,
    background=(8, 7, 9),
    mode="native",
    fps=60,
    fov=78,
    near=0.05,
    far=70,
)

app.light(direction=(-0.35, -0.9, -0.45), color=(255, 238, 210), intensity=1.15)
app.light(direction=(0.8, -0.45, 0.2), color=(80, 135, 255), intensity=0.2)
app.renderer.mesh_cull_distance = 24.0

bullets: list[Bullet] = []
enemy_shots: list[EnemyShot] = []
particles: list[Particle] = []
pickups: list[Pickup] = []
barrels: list[Barrel] = []
covers: list[LowCover] = []
enemies: list[Enemy] = []

player_yaw = 0.0
player_pitch = BASE_PITCH
player_vel_x = 0.0
player_vel_z = 0.0
player_y_offset = 0.0
player_y_velocity = 0.0
player_grounded = True
player_jump_was_down = False
player_coyote_timer = COYOTE_TIME
player_jump_buffer = 0.0
landing_timer = 0.0
health = MAX_HEALTH
ammo = 34
score = 0
shoot_timer = 0.0
muzzle_timer = 0.0
weapon_recoil = 0.0
damage_flash = 0.0
pickup_flash = 0.0
dry_fire_timer = 0.0
bob_time = 0.0
hit_marker_timer = 0.0
game_over = False
victory = False


def add_floor_and_ceiling(row: int, col: int) -> None:
    x, z = cell_center(row, col)
    floor_color = (42, 42, 44) if (row + col) % 2 else (50, 47, 42)
    app.cube(
        position=(x, FLOOR_Y - 0.04, z),
        scale=(TILE, 0.08, TILE),
        color=floor_color,
        ambient=0.4,
    )
    app.cube(
        position=(x, CEILING_Y, z),
        scale=(TILE, 0.08, TILE),
        color=(25, 27, 33),
        ambient=0.34,
    )


def add_wall(row: int, col: int) -> None:
    x, z = cell_center(row, col)
    wall_color = (96, 82, 76) if (row + col) % 2 else (126, 108, 90)
    trim_color = (48, 45, 48) if (row + col) % 2 else (57, 53, 52)
    app.cube(
        position=(x, FLOOR_Y + WALL_HEIGHT * 0.5, z),
        scale=(TILE, WALL_HEIGHT, TILE),
        color=wall_color,
        ambient=0.28,
    )
    app.cube(
        position=(x, FLOOR_Y + 0.08, z),
        scale=(TILE * 1.02, 0.16, TILE * 1.02),
        color=trim_color,
        ambient=0.38,
    )
    app.cube(
        position=(x, FLOOR_Y + WALL_HEIGHT - 0.22, z),
        scale=(TILE * 1.02, 0.1, TILE * 1.02),
        color=(66, 78, 92) if (row + col) % 2 else (88, 74, 96),
        ambient=0.5,
    )


def add_pickup(kind: str, x: float, z: float) -> None:
    if kind == "health":
        color = (74, 220, 92)
        scale = (0.44, 0.24, 0.44)
        amount = 25
    else:
        color = (85, 172, 255)
        scale = (0.46, 0.3, 0.46)
        amount = 18
    mesh = app.cube(
        position=(x, FLOOR_Y + 0.22, z),
        scale=scale,
        color=color,
        ambient=0.7,
    )
    pickups.append(Pickup(mesh, kind, amount, random.random() * math.tau))


def add_barrel(x: float, z: float) -> None:
    body = app.cube(
        position=(x, FLOOR_Y + 0.5, z),
        scale=(0.55, 0.92, 0.55),
        color=(38, 132, 82),
        ambient=0.36,
    )
    band = app.cube(
        position=(x, FLOOR_Y + 0.5, z),
        scale=(0.6, 0.18, 0.6),
        color=(230, 66, 52),
        ambient=0.45,
    )
    barrels.append(Barrel(body, band))


def add_cover(
    x: float,
    z: float,
    height: float = LOW_COVER_HEIGHT,
    color: tuple[int, int, int] = (78, 92, 112),
    trim_color: tuple[int, int, int] = (235, 186, 74),
) -> None:
    body = app.cube(
        position=(x, FLOOR_Y + height * 0.5, z),
        scale=(0.9, height, 0.9),
        color=color,
        ambient=0.43,
    )
    trim = app.cube(
        position=(x, FLOOR_Y + height + 0.03, z),
        scale=(0.96, 0.08, 0.96),
        color=trim_color,
        ambient=0.62,
    )
    covers.append(LowCover(body, trim, height, 0.46))


def create_enemy(x: float, z: float, floor_offset: float = 0.0, stationary: bool = False) -> None:
    base_y = FLOOR_Y + floor_offset
    body = app.cube(
        position=(x, base_y + 0.47, z),
        scale=(0.72, 0.92, 0.58),
        color=(132, 64, 204) if stationary else (172, 42, 40),
        ambient=0.31 if stationary else 0.26,
    )
    head = app.cube(
        position=(x, base_y + 1.14, z),
        scale=(0.56, 0.42, 0.52),
        color=(172, 92, 238) if stationary else (218, 62, 54),
        ambient=0.33 if stationary else 0.28,
    )
    eye_left = app.cube(
        position=(x - 0.14, base_y + 1.2, z - 0.28),
        scale=(0.08, 0.08, 0.05),
        color=(255, 218, 72),
        ambient=0.95,
    )
    eye_right = app.cube(
        position=(x + 0.14, base_y + 1.2, z - 0.28),
        scale=(0.08, 0.08, 0.05),
        color=(255, 218, 72),
        ambient=0.95,
    )
    enemy = Enemy(
        body,
        head,
        eye_left,
        eye_right,
        hp=5 if stationary else 4,
        bob_phase=random.random() * math.tau,
        floor_offset=floor_offset,
        stationary=stationary,
    )
    enemies.append(enemy)
    update_enemy_parts(enemy, 0.0, 0.0)


def build_world() -> None:
    global player_yaw

    for row, line in enumerate(MAP):
        for col, cell in enumerate(line):
            x, z = cell_center(row, col)
            if cell == "#":
                add_wall(row, col)
                continue

            add_floor_and_ceiling(row, col)

            if cell == "P":
                app.camera.position = Vector3(x, EYE_Y, z)
                app.camera.rotation = Vector3(player_pitch, player_yaw, 0)
            elif cell == "E":
                create_enemy(x, z)
            elif cell == "H":
                add_pickup("health", x, z)
            elif cell == "A":
                add_pickup("ammo", x, z)
            elif cell == "B":
                add_barrel(x, z)
            elif cell == "C":
                add_cover(x, z)
            elif cell == "R":
                add_cover(x, z, RAISED_PLATFORM_HEIGHT, (72, 88, 126), (116, 184, 255))
            elif cell == "T":
                add_cover(x, z, RAISED_PLATFORM_HEIGHT, (72, 88, 126), (116, 184, 255))
                create_enemy(x, z, floor_offset=RAISED_PLATFORM_HEIGHT, stationary=True)


def hits_barrel(x: float, z: float, radius: float) -> bool:
    for barrel in barrels:
        pos = barrel.body.position
        dx = pos.x - x
        dz = pos.z - z
        if dx * dx + dz * dz < (radius + 0.44) ** 2:
            return True
    return False


def projectile_hits_barrel(pos: Vector3, radius: float = 0.08) -> Barrel | None:
    for barrel in barrels:
        barrel_pos = barrel.body.position
        if pos.y < FLOOR_Y or pos.y > FLOOR_Y + 1.1:
            continue
        dx = barrel_pos.x - pos.x
        dz = barrel_pos.z - pos.z
        if dx * dx + dz * dz < (0.45 + radius) ** 2:
            return barrel
    return None


def try_move_player(dx: float, dz: float) -> tuple[bool, bool]:
    pos = app.camera.position
    next_x = pos.x + dx
    moved_x = False
    moved_z = False
    if not is_player_blocked(next_x, pos.z, player_y_offset):
        pos = Vector3(next_x, pos.y, pos.z)
        moved_x = True

    next_z = pos.z + dz
    if not is_player_blocked(pos.x, next_z, player_y_offset):
        pos = Vector3(pos.x, pos.y, next_z)
        moved_z = True

    app.camera.position = pos
    return moved_x, moved_z


def try_move_enemy(enemy: Enemy, dx: float, dz: float) -> None:
    pos = enemy.body.position
    next_x = pos.x + dx
    if (
        not is_blocked(next_x, pos.z, radius=0.36)
        and not hits_barrel(next_x, pos.z, 0.36)
        and not hits_low_cover(next_x, pos.z, 0.36, 0.0)
    ):
        pos = Vector3(next_x, pos.y, pos.z)

    next_z = pos.z + dz
    if (
        not is_blocked(pos.x, next_z, radius=0.36)
        and not hits_barrel(pos.x, next_z, 0.36)
        and not hits_low_cover(pos.x, next_z, 0.36, 0.0)
    ):
        pos = Vector3(pos.x, pos.y, next_z)

    enemy.body.position = pos


def update_enemy_parts(enemy: Enemy, delta: float, yaw: float | None = None) -> None:
    enemy.bob_phase += delta * 4.5
    body_pos = enemy.body.position
    floor_y = FLOOR_Y + enemy.floor_offset
    enemy.body.position = Vector3(body_pos.x, floor_y + 0.47, body_pos.z)
    base = enemy.body.position
    body_scale = 1.0 + (0.08 if enemy.hurt_flash > 0 else 0.0)
    bounce = math.sin(enemy.bob_phase) * 0.035
    facing_yaw = enemy.body.rotation.y if yaw is None else yaw
    fx, fz = xz_forward(facing_yaw)
    rx, rz = xz_right(facing_yaw)

    enemy.body.rotation = Vector3(0.0, facing_yaw, 0.0)
    enemy.head.rotation = Vector3(0.0, facing_yaw, 0.0)
    enemy.eye_left.rotation = Vector3(0.0, facing_yaw, 0.0)
    enemy.eye_right.rotation = Vector3(0.0, facing_yaw, 0.0)

    enemy.body.scale = Vector3(0.72 * body_scale, 0.92 * body_scale, 0.58 * body_scale)
    enemy.head.scale = Vector3(0.56 * body_scale, 0.42 * body_scale, 0.52 * body_scale)

    head_pos = Vector3(base.x, floor_y + 1.15 + bounce, base.z)
    enemy.head.position = head_pos
    enemy.eye_left.position = Vector3(
        head_pos.x - rx * 0.16 + fx * 0.29,
        head_pos.y + 0.05,
        head_pos.z - rz * 0.16 + fz * 0.29,
    )
    enemy.eye_right.position = Vector3(
        head_pos.x + rx * 0.16 + fx * 0.29,
        head_pos.y + 0.05,
        head_pos.z + rz * 0.16 + fz * 0.29,
    )


def spawn_particle(
    position: Vector3,
    color: tuple[int, int, int],
    velocity: Vector3 | None = None,
    ttl: float = 0.35,
    size: float = 0.12,
) -> None:
    if len(particles) > 80:
        app.remove(particles.pop(0).mesh)
    if velocity is None:
        velocity = Vector3(
            random.uniform(-2.4, 2.4),
            random.uniform(0.5, 3.2),
            random.uniform(-2.4, 2.4),
        )
    mesh = app.cube(
        position=position.as_tuple(),
        scale=(size, size, size),
        color=color,
        ambient=0.9,
    )
    particles.append(Particle(mesh, velocity, ttl, ttl, size))


def spawn_hit_sparks(position: Vector3) -> None:
    for _ in range(5):
        spawn_particle(position, random.choice(((255, 232, 90), (255, 125, 50), (230, 55, 45))), ttl=0.22, size=0.08)


def spawn_explosion(position: Vector3) -> None:
    for _ in range(24):
        speed = random.uniform(1.2, 5.2)
        angle = random.uniform(0.0, math.tau)
        velocity = Vector3(math.cos(angle) * speed, random.uniform(1.0, 4.8), math.sin(angle) * speed)
        color = random.choice(((255, 228, 80), (255, 126, 38), (218, 47, 35), (92, 92, 88)))
        spawn_particle(position, color, velocity=velocity, ttl=random.uniform(0.32, 0.62), size=random.uniform(0.09, 0.18))


def spawn_pickup_burst(position: Vector3, color: tuple[int, int, int]) -> None:
    for _ in range(10):
        spawn_particle(position, color, ttl=0.28, size=0.07)


def spawn_bullet() -> None:
    global muzzle_timer, weapon_recoil, ammo

    if ammo <= 0:
        return

    ammo -= 1
    direction = app.camera.forward
    right = app.camera.right
    start = app.camera.position + direction * 0.68 + right * 0.08 + Vector3(0.0, -0.08, 0.0)
    bullet_mesh = app.cube(
        position=start.as_tuple(),
        rotation=(player_pitch, player_yaw, 0.0),
        scale=(0.09, 0.09, 0.42),
        color=(255, 226, 86),
        ambient=0.85,
    )
    bullets.append(Bullet(bullet_mesh, direction * BULLET_SPEED, 1.18))
    muzzle_timer = 0.08
    weapon_recoil = min(1.0, weapon_recoil + 0.78)


def spawn_enemy_shot(enemy: Enemy) -> None:
    start = enemy.head.position
    target = app.camera.position + Vector3(0.0, -0.08, 0.0)
    direction = (target - start).normalized()
    shot_mesh = app.cube(
        position=(start + direction * 0.34).as_tuple(),
        rotation=(0.0, enemy.body.rotation.y, 0.0),
        scale=(0.14, 0.14, 0.32),
        color=(255, 74, 82),
        ambient=0.9,
    )
    enemy_shots.append(EnemyShot(shot_mesh, direction * ENEMY_BULLET_SPEED, 1.85))


def remove_bullet(bullet: Bullet) -> None:
    app.remove(bullet.mesh)
    if bullet in bullets:
        bullets.remove(bullet)


def remove_enemy_shot(shot: EnemyShot) -> None:
    app.remove(shot.mesh)
    if shot in enemy_shots:
        enemy_shots.remove(shot)


def remove_pickup(pickup: Pickup) -> None:
    app.remove(pickup.mesh)
    if pickup in pickups:
        pickups.remove(pickup)


def remove_barrel(barrel: Barrel) -> None:
    app.remove(barrel.body)
    app.remove(barrel.band)
    if barrel in barrels:
        barrels.remove(barrel)


def remove_enemy(enemy: Enemy) -> None:
    for mesh in (enemy.body, enemy.head, enemy.eye_left, enemy.eye_right):
        app.remove(mesh)
    if enemy in enemies:
        enemies.remove(enemy)


def explode_barrel(barrel: Barrel) -> None:
    global health, score, damage_flash, game_over, victory

    if barrel.exploded:
        return

    barrel.exploded = True
    center = barrel.body.position
    spawn_explosion(Vector3(center.x, center.y + 0.25, center.z))
    remove_barrel(barrel)

    player_distance = math.sqrt(distance_sq_xz(center, app.camera.position))
    if player_distance < EXPLOSION_RADIUS:
        damage = int((1.0 - player_distance / EXPLOSION_RADIUS) * 38)
        health = max(0, health - damage)
        damage_flash = max(damage_flash, 0.7)
        if health <= 0:
            game_over = True

    for enemy in enemies[:]:
        dist = math.sqrt(distance_sq_xz(center, enemy.body.position))
        if dist < EXPLOSION_RADIUS:
            enemy.hp -= 4 if dist < EXPLOSION_RADIUS * 0.55 else 2
            enemy.hurt_flash = 0.15
            spawn_hit_sparks(enemy.head.position)
            if enemy.hp <= 0:
                remove_enemy(enemy)
                score += 125

    victory = not enemies


def enable_mouse_look() -> None:
    app.pygame.mouse.set_visible(False)
    app.pygame.event.set_grab(True)
    app.pygame.mouse.get_rel()


def update_player(delta: float) -> None:
    global player_yaw, player_pitch, bob_time
    global player_vel_x, player_vel_z, player_y_offset, player_y_velocity
    global player_grounded, player_jump_was_down, player_coyote_timer, player_jump_buffer
    global landing_timer

    turn_speed = 2.65
    mouse_dx, mouse_dy = app.pygame.mouse.get_rel()
    player_yaw -= mouse_dx * MOUSE_SENSITIVITY
    player_pitch = max(
        MOUSE_PITCH_MIN,
        min(MOUSE_PITCH_MAX, player_pitch - mouse_dy * MOUSE_SENSITIVITY),
    )

    if app.key("left") or app.key("q"):
        player_yaw += turn_speed * delta
    if app.key("right") or app.key("e"):
        player_yaw -= turn_speed * delta

    fx, fz = xz_forward(player_yaw)
    rx, rz = xz_right(player_yaw)
    wish_x = wish_z = 0.0
    if app.key("w") or app.key("up"):
        wish_x += fx
        wish_z += fz
    if app.key("s") or app.key("down"):
        wish_x -= fx
        wish_z -= fz
    if app.key("a"):
        wish_x -= rx
        wish_z -= rz
    if app.key("d"):
        wish_x += rx
        wish_z += rz

    wish_len = math.sqrt(wish_x * wish_x + wish_z * wish_z)
    if wish_len > 0.001:
        wish_x /= wish_len
        wish_z /= wish_len

    sprinting = app.key("lshift") or app.key("rshift")
    target_speed = SPRINT_SPEED if sprinting and wish_len > 0.001 else WALK_SPEED
    accel = GROUND_ACCEL if player_grounded else AIR_ACCEL
    if wish_len > 0.001:
        player_vel_x = approach(player_vel_x, wish_x * target_speed, accel * delta)
        player_vel_z = approach(player_vel_z, wish_z * target_speed, accel * delta)
    elif player_grounded:
        player_vel_x = approach(player_vel_x, 0.0, GROUND_FRICTION * delta)
        player_vel_z = approach(player_vel_z, 0.0, GROUND_FRICTION * delta)
    else:
        drag = max(0.0, 1.0 - AIR_DRAG * delta)
        player_vel_x *= drag
        player_vel_z *= drag

    if player_grounded:
        player_coyote_timer = COYOTE_TIME
    else:
        player_coyote_timer = max(0.0, player_coyote_timer - delta)

    jump_down = app.key("space")
    if jump_down and not player_jump_was_down:
        player_jump_buffer = JUMP_BUFFER_TIME
    else:
        player_jump_buffer = max(0.0, player_jump_buffer - delta)

    if player_jump_buffer > 0.0 and player_coyote_timer > 0.0:
        player_y_velocity = JUMP_VELOCITY
        player_grounded = False
        player_coyote_timer = 0.0
        player_jump_buffer = 0.0
        landing_timer = 0.0

    moved_x, moved_z = try_move_player(player_vel_x * delta, player_vel_z * delta)
    if not moved_x:
        player_vel_x = 0.0
    if not moved_z:
        player_vel_z = 0.0

    support_height = support_height_at(app.camera.position.x, app.camera.position.z)
    was_grounded = player_grounded
    player_y_velocity -= GRAVITY * delta
    player_y_offset += player_y_velocity * delta
    ceiling_offset = CEILING_Y - EYE_Y - 0.15
    if player_y_offset > ceiling_offset:
        player_y_offset = ceiling_offset
        player_y_velocity = min(0.0, player_y_velocity)

    if player_y_offset <= support_height:
        if not was_grounded and player_y_velocity < -1.25:
            landing_timer = 0.16
        player_y_offset = support_height
        player_y_velocity = 0.0
        player_grounded = True
    else:
        player_grounded = False

    speed = horizontal_speed()
    moving = speed > 0.18
    if player_grounded and moving:
        bob_time += delta * (7.8 + min(speed, 7.0) * 0.24)
    elif player_grounded:
        bob_time += delta * 2.0
    else:
        bob_time += delta * 1.2

    landing_timer = max(0.0, landing_timer - delta)
    ground_bob = math.sin(bob_time) * (0.044 if moving else 0.012) if player_grounded else 0.0
    landing_bob = -math.sin((landing_timer / 0.16) * math.pi) * 0.045 if landing_timer > 0.0 else 0.0
    app.camera.position = Vector3(
        app.camera.position.x,
        EYE_Y + player_y_offset + ground_bob + landing_bob,
        app.camera.position.z,
    )
    pitch = player_pitch + math.sin(bob_time * 0.5) * 0.008 + damage_flash * 0.025
    app.camera.rotation = Vector3(pitch, player_yaw, 0.0)
    player_jump_was_down = jump_down


def update_shooting(delta: float) -> None:
    global shoot_timer, dry_fire_timer

    shoot_timer = max(0.0, shoot_timer - delta)
    dry_fire_timer = max(0.0, dry_fire_timer - delta)
    trigger = (
        app.pygame.mouse.get_pressed()[0]
        or app.key("f")
        or app.key("lctrl")
        or app.key("rctrl")
    )
    if trigger and shoot_timer <= 0.0:
        if ammo > 0:
            spawn_bullet()
            shoot_timer = 0.13
        else:
            dry_fire_timer = 0.18
            shoot_timer = 0.2


def update_bullets(delta: float) -> None:
    global score, victory, hit_marker_timer

    for bullet in bullets[:]:
        bullet.ttl -= delta
        pos = bullet.mesh.position + bullet.velocity * delta
        bullet.mesh.position = pos

        barrel = projectile_hits_barrel(pos)
        if barrel is not None:
            explode_barrel(barrel)
            remove_bullet(bullet)
            continue

        if bullet.ttl <= 0 or projectile_hits_world(pos, radius=0.08):
            spawn_hit_sparks(pos)
            remove_bullet(bullet)
            continue

        for enemy in enemies[:]:
            head_hit = distance_sq_3d(enemy.head.position, pos) < 0.28
            enemy_floor = FLOOR_Y + enemy.floor_offset
            body_hit = (
                distance_sq_xz(enemy.body.position, pos) < 0.54
                and enemy_floor + 0.05 < pos.y < enemy_floor + 1.15
            )
            if head_hit or body_hit:
                enemy.hp -= 2 if head_hit else 1
                enemy.hurt_flash = 0.12
                hit_marker_timer = 0.17
                score += 12 if head_hit else 5
                spawn_hit_sparks(pos)
                remove_bullet(bullet)
                if enemy.hp <= 0:
                    spawn_explosion(enemy.head.position)
                    remove_enemy(enemy)
                    score += 135 if head_hit else 100
                    victory = not enemies
                break


def update_enemy_shots(delta: float) -> None:
    global health, damage_flash, game_over

    for shot in enemy_shots[:]:
        shot.ttl -= delta
        pos = shot.mesh.position + shot.velocity * delta
        shot.mesh.position = pos
        shot.mesh.rotation = Vector3(shot.mesh.rotation.x + delta * 4.5, shot.mesh.rotation.y, shot.mesh.rotation.z)

        if shot.ttl <= 0 or projectile_hits_world(pos, radius=0.1):
            spawn_hit_sparks(pos)
            remove_enemy_shot(shot)
            continue

        if distance_sq_3d(pos, app.camera.position) < 0.34:
            health = max(0, health - 9)
            damage_flash = 0.72
            remove_enemy_shot(shot)
            if health <= 0:
                game_over = True


def update_particles(delta: float) -> None:
    for particle in particles[:]:
        particle.ttl -= delta
        if particle.ttl <= 0:
            app.remove(particle.mesh)
            particles.remove(particle)
            continue
        particle.velocity = Vector3(
            particle.velocity.x * 0.96,
            particle.velocity.y - 4.6 * delta,
            particle.velocity.z * 0.96,
        )
        particle.mesh.position = particle.mesh.position + particle.velocity * delta
        particle.mesh.rotation = Vector3(
            particle.mesh.rotation.x + delta * 7.0,
            particle.mesh.rotation.y + delta * 4.0,
            particle.mesh.rotation.z,
        )
        scale = particle.size * max(0.12, particle.ttl / particle.life)
        particle.mesh.scale = Vector3(scale, scale, scale)


def update_pickups(delta: float) -> None:
    global health, ammo, pickup_flash, score

    for pickup in pickups[:]:
        pickup.phase += delta * 3.4
        bob = math.sin(pickup.phase) * 0.08
        pickup.mesh.position = Vector3(pickup.mesh.position.x, FLOOR_Y + 0.25 + bob, pickup.mesh.position.z)
        pickup.mesh.rotation = Vector3(0.0, pickup.mesh.rotation.y + delta * 1.8, 0.0)

        if distance_sq_xz(pickup.mesh.position, app.camera.position) > 0.58:
            continue

        if pickup.kind == "health":
            if health >= MAX_HEALTH:
                continue
            health = min(MAX_HEALTH, health + pickup.amount)
            spawn_pickup_burst(pickup.mesh.position, (86, 235, 96))
        else:
            if ammo >= MAX_AMMO:
                continue
            ammo = min(MAX_AMMO, ammo + pickup.amount)
            spawn_pickup_burst(pickup.mesh.position, (80, 178, 255))

        pickup_flash = 0.35
        score += 15
        remove_pickup(pickup)


def update_barrels(delta: float) -> None:
    for barrel in barrels:
        barrel.band.rotation = Vector3(0.0, barrel.band.rotation.y + delta * 0.6, 0.0)


def update_enemies(delta: float) -> None:
    global health, damage_flash, game_over

    player = app.camera.position
    for enemy in enemies[:]:
        enemy.attack_timer = max(0.0, enemy.attack_timer - delta)
        enemy.hurt_flash = max(0.0, enemy.hurt_flash - delta)

        pos = enemy.body.position
        dx = player.x - pos.x
        dz = player.z - pos.z
        distance = math.sqrt(dx * dx + dz * dz)
        yaw = enemy.body.rotation.y

        if distance > 0.001:
            yaw = math.atan2(-dx, -dz)

        visible = has_line_of_sight(pos.x, pos.z, player.x, player.z)
        if visible and not enemy.stationary and 1.05 < distance < 13.5:
            speed = 1.28 if distance < 7.0 else 0.78
            strafe = math.sin(enemy.bob_phase * 0.65 + distance) * (0.38 if distance < 6.0 else 0.18)
            tangent_x = -dz / distance
            tangent_z = dx / distance
            try_move_enemy(
                enemy,
                (dx / distance * speed + tangent_x * strafe) * delta,
                (dz / distance * speed + tangent_z * strafe) * delta,
            )

        if visible and distance <= 1.2 and enemy.attack_timer <= 0.0:
            health = max(0, health - 12)
            damage_flash = 0.85
            enemy.attack_timer = 0.75
            if health <= 0:
                game_over = True
        elif (
            visible
            and 2.1 <= distance <= (12.5 if enemy.stationary else 9.5)
            and enemy.attack_timer <= 0.0
        ):
            spawn_enemy_shot(enemy)
            enemy.attack_timer = random.uniform(0.72, 1.02) if enemy.stationary else random.uniform(0.95, 1.35)

        update_enemy_parts(enemy, delta, yaw)


def update(app: App, delta: float) -> None:
    global muzzle_timer, weapon_recoil, damage_flash, pickup_flash, hit_marker_timer

    muzzle_timer = max(0.0, muzzle_timer - delta)
    weapon_recoil = max(0.0, weapon_recoil - delta * 5.6)
    damage_flash = max(0.0, damage_flash - delta * 2.4)
    pickup_flash = max(0.0, pickup_flash - delta * 2.8)
    hit_marker_timer = max(0.0, hit_marker_timer - delta * 7.0)

    if game_over or victory:
        for shot in enemy_shots[:]:
            remove_enemy_shot(shot)
        update_particles(delta)
        return

    update_player(delta)
    update_shooting(delta)
    update_bullets(delta)
    update_enemy_shots(delta)
    update_particles(delta)
    update_pickups(delta)
    update_barrels(delta)
    update_enemies(delta)


def draw_centered(text: str, y: int, size: int, color: tuple[int, int, int]) -> None:
    surface = app._text_surface(text, color, "consolas", size, bold=True)
    rect = surface.get_rect(center=(app.size[0] // 2, y))
    app.screen.blit(surface, rect)


def draw_bar(
    label: str,
    value: int,
    max_value: int,
    x: int,
    y: int,
    color: tuple[int, int, int],
) -> None:
    pygame = app.pygame
    w, h = 176, 18
    pygame.draw.rect(app.screen, (22, 22, 25), (x, y, w, h), border_radius=3)
    fill = max(0, min(w - 4, int((w - 4) * value / max_value)))
    pygame.draw.rect(app.screen, color, (x + 2, y + 2, fill, h - 4), border_radius=2)
    app.draw_text(f"{label} {value:02d}", (x, y - 26), color=(222, 226, 232), size=22)


def draw_minimap() -> None:
    pygame = app.pygame
    draw = pygame.draw
    cell = 8
    pad = 8
    map_w = MAP_W * cell
    map_h = MAP_H * cell
    x0 = app.size[0] - map_w - pad - 18
    y0 = 18
    draw.rect(app.screen, (13, 14, 17), (x0 - pad, y0 - pad, map_w + pad * 2, map_h + pad * 2), border_radius=4)

    for row, line in enumerate(MAP):
        for col, tile in enumerate(line):
            if tile == "#":
                color = (83, 77, 76)
            elif tile == "R":
                color = (43, 56, 82)
            elif tile == "T":
                color = (70, 48, 94)
            elif tile == "C":
                color = (48, 44, 39)
            else:
                color = (32, 34, 38)
            draw.rect(app.screen, color, (x0 + col * cell, y0 + row * cell, cell - 1, cell - 1))

    for pickup in pickups:
        row, col = world_cell(pickup.mesh.position.x, pickup.mesh.position.z)
        color = (90, 235, 102) if pickup.kind == "health" else (80, 178, 255)
        draw.rect(app.screen, color, (x0 + col * cell + 2, y0 + row * cell + 2, 4, 4))

    for barrel in barrels:
        row, col = world_cell(barrel.body.position.x, barrel.body.position.z)
        draw.circle(app.screen, (224, 80, 56), (x0 + col * cell + 4, y0 + row * cell + 4), 3)

    for cover in covers:
        row, col = world_cell(cover.body.position.x, cover.body.position.z)
        color = (112, 184, 255) if cover.height > LOW_COVER_HEIGHT else (214, 174, 72)
        draw.rect(app.screen, color, (x0 + col * cell + 2, y0 + row * cell + 2, 4, 4))

    for enemy in enemies:
        row, col = world_cell(enemy.body.position.x, enemy.body.position.z)
        color = (188, 92, 255) if enemy.stationary else (220, 54, 50)
        draw.circle(app.screen, color, (x0 + col * cell + 4, y0 + row * cell + 4), 3)

    prow, pcol = world_cell(app.camera.position.x, app.camera.position.z)
    px = x0 + pcol * cell + 4
    py = y0 + prow * cell + 4
    fx, fz = xz_forward(player_yaw)
    draw.circle(app.screen, (255, 230, 104), (px, py), 3)
    draw.line(app.screen, (255, 230, 104), (px, py), (px + int(fx * 8), py - int(fz * 8)), 2)


def overlay(app: App) -> None:
    pygame = app.pygame
    draw = pygame.draw
    width, height = app.size

    if damage_flash > 0:
        surface = pygame.Surface(app.size, pygame.SRCALPHA)
        surface.fill((210, 28, 28, int(120 * min(1.0, damage_flash))))
        app.screen.blit(surface, (0, 0))
    if pickup_flash > 0:
        surface = pygame.Surface(app.size, pygame.SRCALPHA)
        surface.fill((70, 170, 255, int(45 * min(1.0, pickup_flash))))
        app.screen.blit(surface, (0, 0))

    cx, cy = width // 2, height // 2
    spread = 4 + int(10 * weapon_recoil) + (4 if not player_grounded else 0)
    cross_color = (255, 96, 78) if hit_marker_timer > 0 else (238, 235, 210)
    draw.line(app.screen, cross_color, (cx - 16 - spread, cy), (cx - 5 - spread, cy), 2)
    draw.line(app.screen, cross_color, (cx + 5 + spread, cy), (cx + 16 + spread, cy), 2)
    draw.line(app.screen, cross_color, (cx, cy - 16 - spread), (cx, cy - 5 - spread), 2)
    draw.line(app.screen, cross_color, (cx, cy + 5 + spread), (cx, cy + 16 + spread), 2)
    if hit_marker_timer > 0:
        mark = 18
        gap = 6
        draw.line(app.screen, (255, 245, 220), (cx - gap, cy - gap), (cx - mark, cy - mark), 3)
        draw.line(app.screen, (255, 245, 220), (cx + gap, cy - gap), (cx + mark, cy - mark), 3)
        draw.line(app.screen, (255, 245, 220), (cx - gap, cy + gap), (cx - mark, cy + mark), 3)
        draw.line(app.screen, (255, 245, 220), (cx + gap, cy + gap), (cx + mark, cy + mark), 3)

    jump_lift = int(max(0.0, player_y_velocity) * 2.0) if not player_grounded else 0
    gun_base_y = height - 118 + int(weapon_recoil * 22) - jump_lift + int(landing_timer * 120)
    draw.rect(app.screen, (42, 40, 45), (cx - 94, gun_base_y + 42, 188, 96), border_radius=8)
    draw.rect(app.screen, (116, 112, 116), (cx - 34, gun_base_y, 68, 116), border_radius=6)
    draw.rect(app.screen, (31, 30, 34), (cx - 15, gun_base_y + 8, 30, 76), border_radius=4)
    draw.rect(app.screen, (160, 155, 150), (cx - 44, gun_base_y + 40, 88, 26), border_radius=5)
    if muzzle_timer > 0:
        draw.polygon(
            app.screen,
            (255, 232, 80),
            [(cx, gun_base_y - 62), (cx - 38, gun_base_y + 9), (cx + 38, gun_base_y + 9)],
        )
        draw.polygon(
            app.screen,
            (255, 119, 43),
            [(cx, gun_base_y - 32), (cx - 21, gun_base_y + 8), (cx + 21, gun_base_y + 8)],
        )

    draw_bar("HP", health, MAX_HEALTH, 22, 48, (222, 58, 46) if health < 35 else (255, 204, 86))
    draw_bar("AMMO", ammo, MAX_AMMO, 22, 104, (76, 160, 255))
    app.draw_text(f"SCORE {score:04d}", (22, 132), color=(214, 224, 236), size=23)
    app.draw_text(f"ENEMIES {len(enemies)}", (22, 158), color=(214, 224, 236), size=21)
    move_state = "GROUND" if player_grounded else "AIR"
    app.draw_text(f"SPEED {horizontal_speed():04.1f}  {move_state}", (22, 182), color=(220, 214, 170), size=20, cache=False)
    current_fps = 1.0 / app.delta if app.delta > 0 else 0.0
    average_fps = app.frame_index / app.time if app.time > 0 else 0.0
    app.draw_text(f"FPS {current_fps:05.1f}", (22, 206), color=(180, 218, 188), size=20, cache=False)
    app.draw_text(f"AVG {average_fps:05.1f}", (22, 228), color=(180, 218, 188), size=20, cache=False)
    if dry_fire_timer > 0:
        draw_centered("NO AMMO", cy + 52, 24, (255, 94, 72))

    draw_minimap()
    app.draw_text("WASD move  SHIFT sprint  SPACE jump  mouse/Q/E look  click/F fire", (22, height - 34), color=(150, 160, 172), size=20)

    if victory:
        draw_centered("AREA CLEAR", height // 2 - 46, 56, (255, 228, 90))
        draw_centered("Press ESC to quit", height // 2 + 14, 26, (220, 225, 235))
    elif game_over:
        draw_centered("YOU DIED", height // 2 - 46, 58, (230, 48, 40))
        draw_centered("Press ESC to quit", height // 2 + 14, 26, (220, 225, 235))


build_world()

if __name__ == "__main__":
    enable_mouse_look()
    app.run(update=update, overlay=overlay)
