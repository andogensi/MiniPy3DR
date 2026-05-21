"""Beginner lesson 01: show a spinning cube."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minipy3dr import App


app = App(title="Lesson 01 - Spinning Cube")
cube = app.cube(position=(0, 0, -5), size=2, color=(220, 120, 80), ambient=0.22)
app.light(direction=(-0.4, -0.8, -0.6))


def update(app: App, delta: float) -> None:
    app.rotate(cube, x=delta * 0.6, y=delta)


if __name__ == "__main__":
    app.run(update=update)
