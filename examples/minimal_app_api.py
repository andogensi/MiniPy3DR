"""Minimal import-only MiniPy3DR app example."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minipy3dr import MiniPy3DRApp, Vector3


app = MiniPy3DRApp(title="MiniPy3DR - Minimal API")
cube = app.cube(position=(0, 0, -5), size=2.0, color=(220, 120, 80), ambient=0.22)
app.light(direction=(-0.4, -0.8, -0.6), intensity=1.0)


def update(app: MiniPy3DRApp, delta: float) -> None:
    cube.rotation = Vector3(cube.rotation.x + delta * 0.6, cube.rotation.y + delta * 0.9, 0.0)


if __name__ == "__main__":
    app.run(update=update)
