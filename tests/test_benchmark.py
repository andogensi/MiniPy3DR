from __future__ import annotations

from minipy3dr.benchmark import BenchmarkResult, format_results, make_available_cases, make_cube_scene, make_default_cases


def test_default_benchmark_cases_match_native_plan() -> None:
    cases = make_default_cases()

    assert [case.name for case in cases] == ["cube_100", "cube_500", "sphere_obj_1"]


def test_available_benchmark_cases_include_doom_like_example() -> None:
    cases = make_available_cases()

    assert "doom_like_shooter" in [case.name for case in cases]


def test_cube_benchmark_scene_contains_requested_cube_count() -> None:
    scene, camera = make_cube_scene(100, (640, 480))

    assert len(scene.items) == 100
    assert camera.aspect == 640 / 480


def test_benchmark_format_reports_skipped_native_mode() -> None:
    output = format_results(
        [
            BenchmarkResult(
                case_name="cube_100",
                resolution=(640, 480),
                mode="solid_native",
                frames=0,
                seconds=0.0,
                fps=None,
                skipped="not built",
            )
        ]
    )

    assert "solid_native" in output
    assert "skip: not built" in output
