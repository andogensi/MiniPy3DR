"""Render a v0.3 lit cube with keyboard camera controls."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from minipy3dr import KeyboardCameraController, Material, MiniPy3DRApp, Vector3


def main() -> None:
    app = MiniPy3DRApp(size=(800, 600), title="MiniPy3DR v0.3 - Lit Cube Controls")
    controller = KeyboardCameraController(app.camera)
    cube = app.cube(
        position=(0, 0, -5),
        size=2.0,
        material=Material(color=(220, 120, 80), ambient=0.22),
    )
    app.light(direction=(-0.4, -0.8, -0.6), intensity=1.0)

    def update(app: MiniPy3DRApp, delta: float) -> None:
        controller.update(delta)
        cube.rotation = Vector3(cube.rotation.x + delta * 0.5, cube.rotation.y + delta * 0.9, 0)

    app.run(update=update)


if __name__ == "__main__":
    main()
