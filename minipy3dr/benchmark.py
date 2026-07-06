"""Renderer benchmarks for MiniPy3DR.

The benchmark keeps the existing Python and NumPy paths intact so a future
native rasterizer can be added as a third mode and compared directly.
"""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from collections.abc import Callable, Sequence
from dataclasses import dataclass
import importlib
import math
import os
from pathlib import Path
import time
import warnings

from minipy3dr.core import DirectionalLight, Material, Mesh, PerspectiveCamera, Scene
from minipy3dr.loaders import ObjLoadError, load_obj
from minipy3dr.math import Vector3
from minipy3dr.render import Renderer, resolve_render_mode


Resolution = tuple[int, int]
SceneFactory = Callable[[Resolution], tuple[Scene, PerspectiveCamera]]
RendererConfigurator = Callable[[Renderer], None]

DEFAULT_RESOLUTIONS: tuple[Resolution, ...] = ((640, 480), (1280, 720))
DEFAULT_MODES: tuple[str, ...] = ("solid", "solid_numpy", "solid_native")


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    make_scene: SceneFactory
    configure_renderer: RendererConfigurator
    background: tuple[int, int, int] = (16, 18, 24)


@dataclass(frozen=True)
class BenchmarkResult:
    case_name: str
    resolution: Resolution
    mode: str
    frames: int
    seconds: float
    fps: float | None
    skipped: str | None = None


class UnsupportedRenderMode(RuntimeError):
    """Raised when a renderer mode is not available in the current build."""


def make_default_cases() -> tuple[BenchmarkCase, ...]:
    return (
        BenchmarkCase("cube_100", lambda resolution: make_cube_scene(100, resolution), _configure_default_renderer),
        BenchmarkCase("cube_500", lambda resolution: make_cube_scene(500, resolution), _configure_default_renderer),
        BenchmarkCase("sphere_obj_1", make_sphere_or_obj_scene, _configure_default_renderer),
    )


def make_available_cases() -> tuple[BenchmarkCase, ...]:
    return (
        *make_default_cases(),
        BenchmarkCase(
            "doom_like_shooter",
            make_doom_like_shooter_scene,
            _configure_doom_like_renderer,
            background=(8, 7, 9),
        ),
    )


def make_cube_scene(count: int, resolution: Resolution) -> tuple[Scene, PerspectiveCamera]:
    if count <= 0:
        raise ValueError("count must be positive")

    scene = Scene()
    scene.add_light(DirectionalLight(direction=Vector3(-0.35, -0.75, -0.55), intensity=1.0))
    columns = 10
    rows = 10
    per_layer = columns * rows
    spacing_x = 2.0
    spacing_y = 1.55
    layer_spacing = 6.0

    for index in range(count):
        layer = index // per_layer
        local = index % per_layer
        column = local % columns
        row = local // columns
        layer_offset = 0.45 if layer % 2 else 0.0

        cube = Mesh.cube(size=1.0)
        cube.position = Vector3(
            (column - (columns - 1) * 0.5) * spacing_x + layer_offset,
            (row - (rows - 1) * 0.5) * spacing_y,
            -18.0 - layer * layer_spacing,
        )
        cube.rotation = Vector3(0.12 * (index % 5), 0.18 * (index % 7), 0.08 * (index % 3))
        scene.add(cube, material=_material_for_index(index))

    return scene, _make_camera(resolution, far=160.0)


def make_sphere_or_obj_scene(resolution: Resolution) -> tuple[Scene, PerspectiveCamera]:
    scene = Scene()
    scene.add_light(DirectionalLight(direction=Vector3(-0.3, -0.7, -0.6), intensity=1.0))
    mesh = _load_sample_obj() or Mesh.sphere(radius=1.0, segments=32, rings=16)
    mesh.position = Vector3(0.0, 0.0, -4.4)
    mesh.rotation = Vector3(0.25, 0.55, 0.0)
    mesh.scale = Vector3(2.1, 2.1, 2.1)
    scene.add(mesh, Material(color=(150, 205, 255), ambient=0.22))
    return scene, _make_camera(resolution, far=80.0)


def make_doom_like_shooter_scene(resolution: Resolution) -> tuple[Scene, PerspectiveCamera]:
    module = importlib.import_module("examples.doom_like_shooter")
    app = module.app
    app.camera.aspect = resolution[0] / resolution[1]
    return app.scene, app.camera


def run_benchmarks(
    cases: Sequence[BenchmarkCase],
    resolutions: Sequence[Resolution] = DEFAULT_RESOLUTIONS,
    modes: Sequence[str] = DEFAULT_MODES,
    frames: int = 30,
    warmup: int = 3,
    headless: bool = True,
    display: bool = False,
) -> list[BenchmarkResult]:
    if frames <= 0:
        raise ValueError("frames must be positive")
    if warmup < 0:
        raise ValueError("warmup must be non-negative")

    pygame = _init_pygame(headless=headless)
    results: list[BenchmarkResult] = []
    try:
        for resolution in resolutions:
            target, present = _make_target_surface(pygame, resolution, display=display)
            for case in cases:
                for mode in modes:
                    scene, camera = case.make_scene(resolution)
                    renderer = Renderer(resolution, background=case.background)
                    case.configure_renderer(renderer)
                    results.append(
                        _run_one(renderer, scene, camera, target, present, case.name, resolution, mode, frames, warmup)
                    )
    finally:
        pygame.quit()

    return results


def format_results(results: Sequence[BenchmarkResult]) -> str:
    headers = ("case", "resolution", "mode", "frames", "seconds", "fps")
    rows = []
    for result in results:
        resolution = f"{result.resolution[0]}x{result.resolution[1]}"
        if result.skipped is None:
            seconds = f"{result.seconds:.3f}"
            fps = f"{result.fps:.2f}" if result.fps is not None else "n/a"
        else:
            seconds = "-"
            fps = f"skip: {result.skipped}"
        rows.append((result.case_name, resolution, result.mode, str(result.frames), seconds, fps))

    widths = [
        max(len(headers[index]), *(len(row[index]) for row in rows))
        for index in range(len(headers))
    ]
    lines = ["  ".join(header.ljust(widths[index]) for index, header in enumerate(headers))]
    lines.append("  ".join("-" * width for width in widths))
    for row in rows:
        lines.append("  ".join(value.ljust(widths[index]) for index, value in enumerate(row)))
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    cases = _filter_cases(make_available_cases(), args.cases)
    resolutions = _parse_resolutions(args.resolutions)
    results = run_benchmarks(
        cases=cases,
        resolutions=resolutions,
        modes=tuple(args.modes),
        frames=args.frames,
        warmup=args.warmup,
        headless=not args.window,
        display=args.window,
    )
    print("MiniPy3DR renderer benchmark")
    print(format_results(results))
    return 0


def _run_one(
    renderer: Renderer,
    scene: Scene,
    camera: PerspectiveCamera,
    target: object,
    present: Callable[[], None] | None,
    case_name: str,
    resolution: Resolution,
    mode: str,
    frames: int,
    warmup: int,
) -> BenchmarkResult:
    try:
        for _ in range(warmup):
            _render_frame(renderer, scene, camera, target, mode, present)
        start = time.perf_counter()
        for _ in range(frames):
            _render_frame(renderer, scene, camera, target, mode, present)
        seconds = time.perf_counter() - start
    except UnsupportedRenderMode as exc:
        return BenchmarkResult(case_name, resolution, mode, 0, 0.0, None, str(exc))

    fps = frames / seconds if seconds > 0 else math.inf
    return BenchmarkResult(case_name, resolution, mode, frames, seconds, fps)


def _render_frame(
    renderer: Renderer,
    scene: Scene,
    camera: PerspectiveCamera,
    target: object,
    mode: str,
    present: Callable[[], None] | None,
) -> None:
    try:
        renderer.render(scene, camera, target, mode=mode)
        if present is not None:
            present()
    except ValueError as exc:
        if _is_native_mode(mode):
            raise UnsupportedRenderMode("not built") from exc
        raise
    except RuntimeError as exc:
        if _is_native_mode(mode):
            raise UnsupportedRenderMode(str(exc)) from exc
        raise


def _is_native_mode(mode: str) -> bool:
    try:
        return resolve_render_mode(mode) == "solid_native"
    except ValueError:
        return False


def _init_pygame(headless: bool) -> object:
    if headless:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="pkg_resources is deprecated as an API.*")
        import pygame

    pygame.init()
    return pygame


def _make_target_surface(pygame: object, resolution: Resolution, display: bool) -> tuple[object, Callable[[], None] | None]:
    if display:
        return pygame.display.set_mode(resolution), pygame.display.flip
    return pygame.Surface(resolution), None


def _make_camera(resolution: Resolution, far: float) -> PerspectiveCamera:
    return PerspectiveCamera(
        fov=70.0,
        aspect=resolution[0] / resolution[1],
        near=0.1,
        far=far,
    )


def _material_for_index(index: int) -> Material:
    return Material(
        color=(
            90 + (index * 37) % 130,
            95 + (index * 53) % 120,
            115 + (index * 29) % 110,
        ),
        ambient=0.2,
    )


def _configure_default_renderer(renderer: Renderer) -> None:
    del renderer


def _configure_doom_like_renderer(renderer: Renderer) -> None:
    renderer.mesh_cull_distance = 16.0


def _load_sample_obj() -> Mesh | None:
    asset_path = Path(__file__).resolve().parents[1] / "assets" / "sphere.obj"
    if not asset_path.exists():
        return None
    try:
        return load_obj(asset_path)
    except ObjLoadError:
        return None


def _parse_args(argv: Sequence[str] | None) -> Namespace:
    parser = ArgumentParser(description="Benchmark MiniPy3DR renderer modes.")
    parser.add_argument("--frames", type=int, default=30, help="Measured frames per benchmark cell.")
    parser.add_argument("--warmup", type=int, default=3, help="Warmup frames before measurement.")
    parser.add_argument(
        "--cases",
        nargs="+",
        default=["cube_100", "cube_500", "sphere_obj_1"],
        help="Benchmark cases to run.",
    )
    parser.add_argument(
        "--modes",
        nargs="+",
        default=list(DEFAULT_MODES),
        help="Renderer modes to run.",
    )
    parser.add_argument(
        "--resolutions",
        nargs="+",
        default=[f"{width}x{height}" for width, height in DEFAULT_RESOLUTIONS],
        help="Resolutions like 640x480.",
    )
    parser.add_argument(
        "--window",
        action="store_true",
        help="Render to a visible pygame window instead of an offscreen Surface.",
    )
    return parser.parse_args(argv)


def _filter_cases(cases: Sequence[BenchmarkCase], names: Sequence[str]) -> tuple[BenchmarkCase, ...]:
    by_name = {case.name: case for case in cases}
    missing = [name for name in names if name not in by_name]
    if missing:
        raise SystemExit(f"unknown benchmark case: {', '.join(missing)}")
    return tuple(by_name[name] for name in names)


def _parse_resolutions(values: Sequence[str]) -> tuple[Resolution, ...]:
    resolutions: list[Resolution] = []
    for value in values:
        parts = value.lower().split("x", 1)
        if len(parts) != 2:
            raise SystemExit(f"invalid resolution: {value}")
        try:
            width = int(parts[0])
            height = int(parts[1])
        except ValueError as exc:
            raise SystemExit(f"invalid resolution: {value}") from exc
        if width <= 0 or height <= 0:
            raise SystemExit(f"invalid resolution: {value}")
        resolutions.append((width, height))
    return tuple(resolutions)


if __name__ == "__main__":
    raise SystemExit(main())
