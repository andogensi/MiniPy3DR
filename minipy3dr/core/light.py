"""Light types used by MiniPy3DR scenes."""

from __future__ import annotations

from dataclasses import dataclass, field

from minipy3dr.core.material import Color
from minipy3dr.math import Vector3


@dataclass(frozen=True)
class DirectionalLight:
    """A light with parallel rays.

    ``direction`` describes the direction the light rays travel in world space.
    For example, ``Vector3(0, 0, -1)`` lights faces whose normals point toward
    ``+Z``.
    """

    direction: Vector3 = field(default_factory=lambda: Vector3(-0.4, -0.8, -0.6))
    color: Color = (255, 255, 255)
    intensity: float = 1.0

    def __post_init__(self) -> None:
        if self.direction.length() == 0:
            raise ValueError("DirectionalLight direction must be non-zero")
        if self.intensity < 0:
            raise ValueError("DirectionalLight intensity must be non-negative")
