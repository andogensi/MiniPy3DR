"""Beginner lesson 03: a tiny collect game."""

from __future__ import annotations

from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minipy3dr import App


app = App(title="Lesson 03 - Collect Game", background=(8, 10, 16))
player = app.cube(position=(0, -1.2, -5), size=1.0, color=(80, 210, 255), ambient=0.22)
coin = app.cube(position=(1.8, 0.8, -5), size=0.55, color=(255, 210, 70), ambient=0.25)
app.light(direction=(-0.4, -0.8, -0.6))

score = 0


def update(app: App, delta: float) -> None:
    global score

    speed = 3.2
    if app.key("left") or app.key("a"):
        app.move(player, x=-speed * delta)
    if app.key("right") or app.key("d"):
        app.move(player, x=speed * delta)
    if app.key("up") or app.key("w"):
        app.move(player, y=speed * delta)
    if app.key("down") or app.key("s"):
        app.move(player, y=-speed * delta)

    player_x = max(-3.0, min(3.0, player.position.x))
    player_y = max(-1.8, min(1.8, player.position.y))
    app.set_position(player, player_x, player_y, -5)
    app.rotate(player, y=delta * 1.8)
    app.rotate(coin, x=delta * 2.0, y=delta * 2.8)

    dx = player.position.x - coin.position.x
    dy = player.position.y - coin.position.y
    if dx * dx + dy * dy < 0.55:
        score += 1
        app.set_position(coin, random.uniform(-2.8, 2.8), random.uniform(-1.5, 1.5), -5)


def overlay(app: App) -> None:
    app.draw_text(f"SCORE {score}", (20, 20), size=28)
    app.draw_text("Collect the yellow cube", (20, 54), color=(180, 200, 230), size=22)


if __name__ == "__main__":
    app.run(update=update, overlay=overlay)
