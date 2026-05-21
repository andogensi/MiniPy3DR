"""Projection helpers for the renderer."""

from __future__ import annotations

from dataclasses import dataclass

from minipy3dr.math import Vector3


@dataclass(frozen=True)
class ProjectedVertex:
    view: Vector3
    screen: tuple[float, float, float] | None


def viewport_transform(ndc: Vector3, width: int, height: int) -> tuple[float, float, float]:
    x = (ndc.x + 1.0) * 0.5 * (width - 1)
    y = (1.0 - ndc.y) * 0.5 * (height - 1)
    depth = (ndc.z + 1.0) * 0.5
    return (x, y, depth)
