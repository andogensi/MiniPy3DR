"""NumPy-backed triangle rasterization."""

from __future__ import annotations

import math

import numpy as np

from minipy3dr.core.material import Color


ScreenVertex = tuple[float, float, float]


class NumpyFrameBuffer:
    def __init__(self, width: int, height: int, background: Color) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("frame buffer dimensions must be positive")
        self.width = width
        self.height = height
        self.color = np.empty((height, width, 3), dtype=np.uint8)
        self.depth = np.empty((height, width), dtype=np.float32)
        self._pixel_x = np.arange(width, dtype=np.float32) + 0.5
        self._pixel_y = np.arange(height, dtype=np.float32) + 0.5
        self.clear(background)

    def clear(self, background: Color) -> None:
        self.color[:, :] = background
        self.depth.fill(np.inf)

    def fill_triangle(
        self,
        a: ScreenVertex,
        b: ScreenVertex,
        c: ScreenVertex,
        color: Color,
    ) -> None:
        min_x = max(0, math.floor(min(a[0], b[0], c[0])))
        max_x = min(self.width - 1, math.ceil(max(a[0], b[0], c[0])))
        min_y = max(0, math.floor(min(a[1], b[1], c[1])))
        max_y = min(self.height - 1, math.ceil(max(a[1], b[1], c[1])))
        if min_x > max_x or min_y > max_y:
            return

        denominator = (
            (b[1] - c[1]) * (a[0] - c[0])
            + (c[0] - b[0]) * (a[1] - c[1])
        )
        if denominator == 0:
            return
        inv_denominator = 1.0 / denominator

        px = self._pixel_x[min_x : max_x + 1][None, :]
        py = self._pixel_y[min_y : max_y + 1][:, None]

        weight_a = (
            (b[1] - c[1]) * (px - c[0])
            + (c[0] - b[0]) * (py - c[1])
        ) * inv_denominator
        weight_b = (
            (c[1] - a[1]) * (px - c[0])
            + (a[0] - c[0]) * (py - c[1])
        ) * inv_denominator
        weight_c = 1.0 - weight_a - weight_b

        inside = (weight_a >= -1e-6) & (weight_b >= -1e-6) & (weight_c >= -1e-6)
        depth = weight_a * a[2] + weight_b * b[2] + weight_c * c[2]
        depth_region = self.depth[min_y : max_y + 1, min_x : max_x + 1]
        color_region = self.color[min_y : max_y + 1, min_x : max_x + 1]
        update = inside & (depth < depth_region)
        if not update.any():
            return

        depth_region[update] = depth[update]
        color_region[update] = color

    def blit_to_surface(self, target: object) -> None:
        import pygame

        pygame.surfarray.blit_array(target, self.color.swapaxes(0, 1))
