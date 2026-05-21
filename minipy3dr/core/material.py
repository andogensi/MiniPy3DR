"""Simple material data for v0.2 flat color rendering."""

from __future__ import annotations

from dataclasses import dataclass


Color = tuple[int, int, int]


@dataclass(frozen=True)
class Material:
    color: Color = (220, 120, 80)
