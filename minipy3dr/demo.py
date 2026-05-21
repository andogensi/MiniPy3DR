"""Small demo used by ``python -m minipy3dr`` and ``minipy3dr-demo``."""

from __future__ import annotations

from minipy3dr.app import MiniPy3DRApp


def main() -> None:
    app = MiniPy3DRApp(title="MiniPy3DR Demo", render_scale=0.8)
    cube = app.cube(position=(0, 0, -5), size=2.0, color=(220, 120, 80), ambient=0.22)
    app.light(direction=(-0.4, -0.8, -0.6), intensity=1.0)

    def update(app: MiniPy3DRApp, delta: float) -> None:
        app.rotate(cube, x=delta * 0.6, y=delta)

    app.run(update=update)


if __name__ == "__main__":
    main()
