"""Depth buffer for software rasterization."""

from __future__ import annotations

import math


class ZBuffer:
    def __init__(self, width: int, height: int) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("ZBuffer dimensions must be positive")
        self.width = width
        self.height = height
        self._values = [[math.inf for _ in range(width)] for _ in range(height)]

    def clear(self) -> None:
        for row in self._values:
            for index in range(self.width):
                row[index] = math.inf

    def get(self, x: int, y: int) -> float:
        return self._values[y][x]

    def test_and_set(self, x: int, y: int, depth: float) -> bool:
        if depth < self._values[y][x]:
            self._values[y][x] = depth
            return True
        return False
