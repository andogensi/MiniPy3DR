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
BULLET_SPEED = 21.0
MAX_HEALTH = 100
MAX_AMMO = 70
EXPLOSION_RADIUS = 3.2

MAP = [
    "##############",
    "#P.A.#.......#",
    "#.##.#.###H#.#",
    "#....#...#.#.#",
    "####.###.#.#.#",
    "#..B...#...#.#",
    "#.####.###.#.#",
    "#...E...B..#.#",
    "#.###.##E###.#",
    "#..H..#...A..#",
    "#..E....B....#",
    "##############",
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
class Enemy:
    body: Mesh
    head: Mesh
    eye_left: Mesh
    eye_right: Mesh
    hp: int = 4
    attack_timer: float = 0.0
    hurt_flash: float = 0.0
    bob_phase: float = 0.0


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


app = App(
    size=(960, 600),
    title="Mini DOOM-like Shooter",
    render_scale=0.6,
    background=(8, 7, 9),
    mode="solid_numpy",
    fps=60,
    fov=78,
    near=0.05,
    far=70,
)

app.light(direction=(-0.35, -0.9, -0.45), color=(255, 238, 210), intensity=1.15)
app.light(direction=(0.8, -0.45, 0.2), color=(80, 135, 255), intensity=0.2)
app.renderer.mesh_cull_distance = 16.0

bullets: list[Bullet] = []
particles: list[Particle] = []
pickups: list[Pickup] = []
barrels: list[Barrel] = []
enemies: list[Enemy] = []

player_yaw = 0.0
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


def create_enemy(x: float, z: float) -> None:
    body = app.cube(
        position=(x, FLOOR_Y + 0.47, z),
        scale=(0.72, 0.92, 0.58),
        color=(172, 42, 40),
        ambient=0.26,
    )
    head = app.cube(
        position=(x, FLOOR_Y + 1.14, z),
        scale=(0.56, 0.42, 0.52),
        color=(218, 62, 54),
        ambient=0.28,
    )
    eye_left = app.cube(
        position=(x - 0.14, FLOOR_Y + 1.2, z - 0.28),
        scale=(0.08, 0.08, 0.05),
        color=(255, 218, 72),
        ambient=0.95,
    )
    eye_right = app.cube(
        position=(x + 0.14, FLOOR_Y + 1.2, z - 0.28),
        scale=(0.08, 0.08, 0.05),
        color=(255, 218, 72),
        ambient=0.95,
    )
    enemy = Enemy(body, head, eye_left, eye_right, bob_phase=random.random() * math.tau)
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
                app.camera.rotation = Vector3(-0.035, player_yaw, 0)
            elif cell == "E":
                create_enemy(x, z)
            elif cell == "H":
                add_pickup("health", x, z)
            elif cell == "A":
                add_pickup("ammo", x, z)
            elif cell == "B":
                add_barrel(x, z)


def hits_barrel(x: float, z: float, radius: float) -> bool:
    for barrel in barrels:
        pos = barrel.body.position
        dx = pos.x - x
        dz = pos.z - z
        if dx * dx + dz * dz < (radius + 0.44) ** 2:
            return True
    return False


def try_move_player(dx: float, dz: float) -> None:
    pos = app.camera.position
    next_x = pos.x + dx
    if not is_blocked(next_x, pos.z) and not hits_barrel(next_x, pos.z, PLAYER_RADIUS):
        pos = Vector3(next_x, pos.y, pos.z)

    next_z = pos.z + dz
    if not is_blocked(pos.x, next_z) and not hits_barrel(pos.x, next_z, PLAYER_RADIUS):
        pos = Vector3(pos.x, pos.y, next_z)

    app.camera.position = pos


def try_move_enemy(enemy: Enemy, dx: float, dz: float) -> None:
    pos = enemy.body.position
    next_x = pos.x + dx
    if not is_blocked(next_x, pos.z, radius=0.36) and not hits_barrel(next_x, pos.z, 0.36):
        pos = Vector3(next_x, pos.y, pos.z)

    next_z = pos.z + dz
    if not is_blocked(pos.x, next_z, radius=0.36) and not hits_barrel(pos.x, next_z, 0.36):
        pos = Vector3(pos.x, pos.y, next_z)

    enemy.body.position = pos


def update_enemy_parts(enemy: Enemy, delta: float, yaw: float | None = None) -> None:
    enemy.bob_phase += delta * 4.5
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

    head_pos = Vector3(base.x, FLOOR_Y + 1.15 + bounce, base.z)
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
    fx, fz = xz_forward(player_yaw)
    start = app.camera.position + Vector3(fx * 0.65, -0.07, fz * 0.65)
    bullet_mesh = app.cube(
        position=start.as_tuple(),
        rotation=(0.0, player_yaw, 0.0),
        scale=(0.1, 0.1, 0.38),
        color=(255, 226, 86),
        ambient=0.85,
    )
    bullets.append(Bullet(bullet_mesh, Vector3(fx * BULLET_SPEED, 0.0, fz * BULLET_SPEED), 1.18))
    muzzle_timer = 0.08
    weapon_recoil = min(1.0, weapon_recoil + 0.78)


def remove_bullet(bullet: Bullet) -> None:
    app.remove(bullet.mesh)
    if bullet in bullets:
        bullets.remove(bullet)


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


def update_player(delta: float) -> None:
    global player_yaw, bob_time

    turn_speed = 2.65
    move_speed = 4.35
    if app.key("left") or app.key("q"):
        player_yaw += turn_speed * delta
    if app.key("right") or app.key("e"):
        player_yaw -= turn_speed * delta

    fx, fz = xz_forward(player_yaw)
    rx, rz = xz_right(player_yaw)
    dx = dz = 0.0
    if app.key("w") or app.key("up"):
        dx += fx * move_speed * delta
        dz += fz * move_speed * delta
    if app.key("s") or app.key("down"):
        dx -= fx * move_speed * delta
        dz -= fz * move_speed * delta
    if app.key("a"):
        dx -= rx * move_speed * delta
        dz -= rz * move_speed * delta
    if app.key("d"):
        dx += rx * move_speed * delta
        dz += rz * move_speed * delta

    moving = dx * dx + dz * dz > 0.000001
    if moving:
        bob_time += delta * 8.5
    else:
        bob_time += delta * 2.0

    try_move_player(dx, dz)
    bob = math.sin(bob_time) * 0.045 if moving else math.sin(bob_time) * 0.012
    app.camera.position = Vector3(app.camera.position.x, EYE_Y + bob, app.camera.position.z)
    pitch = -0.035 + math.sin(bob_time * 0.5) * 0.008 + damage_flash * 0.025
    app.camera.rotation = Vector3(pitch, player_yaw, 0.0)


def update_shooting(delta: float) -> None:
    global shoot_timer, dry_fire_timer

    shoot_timer = max(0.0, shoot_timer - delta)
    dry_fire_timer = max(0.0, dry_fire_timer - delta)
    trigger = app.key("space") or app.pygame.mouse.get_pressed()[0]
    if trigger and shoot_timer <= 0.0:
        if ammo > 0:
            spawn_bullet()
            shoot_timer = 0.15
        else:
            dry_fire_timer = 0.18
            shoot_timer = 0.2


def update_bullets(delta: float) -> None:
    global score, victory

    for bullet in bullets[:]:
        bullet.ttl -= delta
        pos = bullet.mesh.position + bullet.velocity * delta
        bullet.mesh.position = pos

        if bullet.ttl <= 0 or is_blocked(pos.x, pos.z, radius=0.08):
            spawn_hit_sparks(pos)
            remove_bullet(bullet)
            continue

        removed = False
        for barrel in barrels[:]:
            if distance_sq_xz(barrel.body.position, pos) < 0.48:
                explode_barrel(barrel)
                remove_bullet(bullet)
                removed = True
                break
        if removed:
            continue

        for enemy in enemies[:]:
            if distance_sq_xz(enemy.body.position, pos) < 0.56:
                enemy.hp -= 1
                enemy.hurt_flash = 0.12
                spawn_hit_sparks(pos)
                remove_bullet(bullet)
                if enemy.hp <= 0:
                    spawn_explosion(enemy.head.position)
                    remove_enemy(enemy)
                    score += 100
                    victory = not enemies
                break


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
        if visible and 1.05 < distance < 13.5:
            speed = 1.28 if distance < 7.0 else 0.78
            try_move_enemy(enemy, dx / distance * speed * delta, dz / distance * speed * delta)

        if visible and distance <= 1.2 and enemy.attack_timer <= 0.0:
            health = max(0, health - 12)
            damage_flash = 0.85
            enemy.attack_timer = 0.75
            if health <= 0:
                game_over = True

        update_enemy_parts(enemy, delta, yaw)


def update(app: App, delta: float) -> None:
    global muzzle_timer, weapon_recoil, damage_flash, pickup_flash

    muzzle_timer = max(0.0, muzzle_timer - delta)
    weapon_recoil = max(0.0, weapon_recoil - delta * 5.6)
    damage_flash = max(0.0, damage_flash - delta * 2.4)
    pickup_flash = max(0.0, pickup_flash - delta * 2.8)

    if game_over or victory:
        update_particles(delta)
        return

    update_player(delta)
    update_shooting(delta)
    update_bullets(delta)
    update_particles(delta)
    update_pickups(delta)
    update_barrels(delta)
    update_enemies(delta)


def draw_centered(text: str, y: int, size: int, color: tuple[int, int, int]) -> None:
    font = app.pygame.font.SysFont("consolas", size, bold=True)
    surface = font.render(text, True, color)
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
            color = (83, 77, 76) if tile == "#" else (32, 34, 38)
            draw.rect(app.screen, color, (x0 + col * cell, y0 + row * cell, cell - 1, cell - 1))

    for pickup in pickups:
        row, col = world_cell(pickup.mesh.position.x, pickup.mesh.position.z)
        color = (90, 235, 102) if pickup.kind == "health" else (80, 178, 255)
        draw.rect(app.screen, color, (x0 + col * cell + 2, y0 + row * cell + 2, 4, 4))

    for barrel in barrels:
        row, col = world_cell(barrel.body.position.x, barrel.body.position.z)
        draw.circle(app.screen, (224, 80, 56), (x0 + col * cell + 4, y0 + row * cell + 4), 3)

    for enemy in enemies:
        row, col = world_cell(enemy.body.position.x, enemy.body.position.z)
        draw.circle(app.screen, (220, 54, 50), (x0 + col * cell + 4, y0 + row * cell + 4), 3)

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
    spread = 4 + int(10 * weapon_recoil)
    cross_color = (238, 235, 210)
    draw.line(app.screen, cross_color, (cx - 16 - spread, cy), (cx - 5 - spread, cy), 2)
    draw.line(app.screen, cross_color, (cx + 5 + spread, cy), (cx + 16 + spread, cy), 2)
    draw.line(app.screen, cross_color, (cx, cy - 16 - spread), (cx, cy - 5 - spread), 2)
    draw.line(app.screen, cross_color, (cx, cy + 5 + spread), (cx, cy + 16 + spread), 2)

    gun_base_y = height - 118 + int(weapon_recoil * 22)
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
    if dry_fire_timer > 0:
        draw_centered("NO AMMO", cy + 52, 24, (255, 94, 72))

    draw_minimap()
    app.draw_text("WASD move  Q/E turn  SPACE fire  barrels explode", (22, height - 34), color=(150, 160, 172), size=20)

    if victory:
        draw_centered("AREA CLEAR", height // 2 - 46, 56, (255, 228, 90))
        draw_centered("Press ESC to quit", height // 2 + 14, 26, (220, 225, 235))
    elif game_over:
        draw_centered("YOU DIED", height // 2 - 46, 58, (230, 48, 40))
        draw_centered("Press ESC to quit", height // 2 + 14, 26, (220, 225, 235))


build_world()

if __name__ == "__main__":
    app.run(update=update, overlay=overlay)
