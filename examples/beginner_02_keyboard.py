"""Beginner lesson 02: move a cube with the keyboard."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minipy3dr import App


app = App(title="Lesson 02 - Keyboard Move")
player = app.cube(position=(0, 0, -5), size=1.4, color=(80, 210, 255), ambient=0.22)
app.light(direction=(-0.4, -0.8, -0.6))


def update(app: App, delta: float) -> None:
    speed = 3.0
    if app.key("left") or app.key("a"):
        app.move(player, x=-speed * delta)
    if app.key("right") or app.key("d"):
        app.move(player, x=speed * delta)
    if app.key("up") or app.key("w"):
        app.move(player, y=speed * delta)
    if app.key("down") or app.key("s"):
        app.move(player, y=-speed * delta)

    app.rotate(player, x=delta * 0.8, y=delta * 1.2)


def overlay(app: App) -> None:
    app.draw_text("Move: arrow keys / WASD", (20, 20), size=24)


if __name__ == "__main__":
    app.run(update=update, overlay=overlay)
