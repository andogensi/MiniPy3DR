# MiniPy3DR

MiniPy3DR is a tiny software 3D renderer for Pygame surfaces.
It is designed for lessons, prototypes, and small games where students can see
the basics of cameras, meshes, lights, flat shading, and z-buffer rendering.

## Install

From GitHub:

```powershell
python -m pip install "git+https://github.com/OWNER/MiniPy3DR.git"
```

From a specific branch or tag:

```powershell
python -m pip install "git+https://github.com/OWNER/MiniPy3DR.git@main"
python -m pip install "git+https://github.com/OWNER/MiniPy3DR.git@v0.3.0"
```

From this repository:

```powershell
python -m pip install .
```

For classroom development, use editable install:

```powershell
python -m pip install -e .
```

After that, student files can simply import the beginner API:

```python
from minipy3dr import App
```

## Quick Start

```python
from minipy3dr import App

app = App(title="MiniPy3DR")
cube = app.cube(position=(0, 0, -5), size=2, color=(220, 120, 80), ambient=0.22)
app.light(direction=(-0.4, -0.8, -0.6))


def update(app, delta):
    app.rotate(cube, y=delta)


app.run(update=update)
```

## Run the Demo

```powershell
python -m minipy3dr
```

or, after installation:

```powershell
minipy3dr-demo
```

## Beginner Lessons

- `docs/beginner_api.md`
- `docs/classroom_setup.md`
- `examples/beginner_01_cube.py`
- `examples/beginner_02_keyboard.py`
- `examples/beginner_03_collect_game.py`

## Build

```powershell
python -m pip install -e ".[dev]"
python -m build
```

The wheel and source archive will be written to `dist/`.
