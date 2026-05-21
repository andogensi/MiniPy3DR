"""Simple material data for flat shaded rendering."""

from __future__ import annotations

from dataclasses import dataclass


Color = tuple[int, int, int]


@dataclass(frozen=True)
class Material:
    color: Color = (220, 120, 80)
    ambient: float = 0.18
