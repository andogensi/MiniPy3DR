# MiniPy3DR

MiniPy3DR is a tiny software 3D renderer for Pygame surfaces.
It is designed for lessons, prototypes, and small games where students can see
the basics of cameras, meshes, lights, flat shading, and z-buffer rendering.

## Install

Recommended for Windows classroom PCs:

```powershell
python -m pip install minipy3dr
```

This installs the matching prebuilt Windows wheel from PyPI for 64-bit Python
3.10, 3.11, 3.12, or 3.13. Students do not need Visual Studio Build Tools.

To pin a specific version for a class:

```powershell
python -m pip install "minipy3dr==0.4.0"
```

Check that the native renderer is available:

```powershell
python -c "from minipy3dr.render import is_native_available; print(is_native_available())"
```

With uv:

```powershell
uv pip install minipy3dr
```

Installing from GitHub source is useful for teachers and development, but it is
not the recommended classroom default because pip builds the C++ extension on
the local PC:

```powershell
python -m pip install "git+https://github.com/andogensi/MiniPy3DR.git"
```

With uv:

```powershell
uv pip install "git+https://github.com/andogensi/MiniPy3DR.git"
```

From a specific branch or tag:

```powershell
python -m pip install "git+https://github.com/andogensi/MiniPy3DR.git@main"
python -m pip install "git+https://github.com/andogensi/MiniPy3DR.git@v0.4.0"
```

From this repository:

```powershell
python -m pip install .
```

For classroom development, use editable install:

```powershell
python -m pip install -e .
```

or with uv:

```powershell
uv pip install -e .
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

## Load OBJ Meshes

```python
from minipy3dr import App

app = App(title="OBJ demo")
model = app.obj("assets/model.obj", position=(0, 0, -6), color=(160, 210, 255))
app.light(direction=(-0.4, -0.8, -0.6))


def update(app, delta):
    app.rotate(model, y=delta)


app.run(update=update)
```

For lower-level code, use `load_obj(path)` to get a `Mesh`:

```python
from minipy3dr import load_obj

mesh = load_obj("assets/model.obj")
```

## Run the Demo

```powershell
python -m minipy3dr
```

or, after installation:

```powershell
minipy3dr-demo
```

## Renderer Benchmark

Compare the current renderer modes before changing the rasterizer:

```powershell
python -m minipy3dr.benchmark
```

or, after installation:

```powershell
minipy3dr-benchmark
```

The default benchmark runs these cases at `640x480` and `1280x720`:

- `cube_100`
- `cube_500`
- `sphere_obj_1`

You can also run the heavier example scene with `--cases doom_like_shooter`.

It measures `solid`, `solid_numpy`, and `solid_native`. `solid_native` uses the
C++ extension when it is built; otherwise it is reported as skipped.

From source, install or rebuild the project to compile the native extension:

```powershell
python -m pip install -e .
```

For a quick smoke run:

```powershell
python -m minipy3dr.benchmark --frames 1 --warmup 0 --cases sphere_obj_1 --resolutions 640x480
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

With uv:

```powershell
uv pip install -e ".[dev]"
uv run python -m build
```

The wheel and source archive will be written to `dist/`.

## Publish to PyPI

Windows wheels are built by GitHub Actions and published to PyPI on version
tags. Before the first release, configure a PyPI trusted publisher or pending
publisher for repository `andogensi/MiniPy3DR`, workflow `wheels.yml`, and
environment `pypi`.

To publish a new version, update the version in `pyproject.toml` and
`minipy3dr/__init__.py`, then push a tag:

```powershell
git tag v0.4.0
git push origin main
git push origin v0.4.0
```

The `Build and publish package` workflow uploads `cp310`, `cp311`, `cp312`, and
`cp313` Windows `win_amd64` wheels plus the source distribution to PyPI. Those
wheels include the C++ native renderer, so students can use `pip install
minipy3dr` without Visual Studio Build Tools.

The workflow uses PyPI trusted publishing with the `pypi` GitHub Environment.
It sets `MINIPY3DR_REQUIRE_NATIVE=1`, so PyPI wheels fail to build if the native
extension is missing. Source installs keep the extension optional and fall back
to the Python/NumPy renderer when no compiler is available.
