"""Triangle and line rasterization helpers."""

from __future__ import annotations

from minipy3dr.core.material import Color
from minipy3dr.render.zbuffer import ZBuffer


ScreenVertex = tuple[float, float, float]


class Rasterizer:
    @staticmethod
    def draw_line(target: object, start: tuple[float, float], end: tuple[float, float], color: Color) -> None:
        x0 = int(round(start[0]))
        y0 = int(round(start[1]))
        x1 = int(round(end[0]))
        y1 = int(round(end[1]))

        dx = abs(x1 - x0)
        sx = 1 if x0 < x1 else -1
        dy = -abs(y1 - y0)
        sy = 1 if y0 < y1 else -1
        error = dx + dy

        while True:
            Rasterizer._set_pixel(target, x0, y0, color)
            if x0 == x1 and y0 == y1:
                break
            doubled_error = 2 * error
            if doubled_error >= dy:
                error += dy
                x0 += sx
            if doubled_error <= dx:
                error += dx
                y0 += sy

    @staticmethod
    def fill_triangle(
        target: object,
        a: ScreenVertex,
        b: ScreenVertex,
        c: ScreenVertex,
        color: Color,
        zbuffer: ZBuffer,
    ) -> None:
        min_x = max(0, int(min(a[0], b[0], c[0])))
        max_x = min(zbuffer.width - 1, int(max(a[0], b[0], c[0])) + 1)
        min_y = max(0, int(min(a[1], b[1], c[1])))
        max_y = min(zbuffer.height - 1, int(max(a[1], b[1], c[1])) + 1)

        denominator = (
            (b[1] - c[1]) * (a[0] - c[0])
            + (c[0] - b[0]) * (a[1] - c[1])
        )
        if denominator == 0:
            return

        for y in range(min_y, max_y + 1):
            py = y + 0.5
            for x in range(min_x, max_x + 1):
                px = x + 0.5
                weight_a = (
                    (b[1] - c[1]) * (px - c[0])
                    + (c[0] - b[0]) * (py - c[1])
                ) / denominator
                weight_b = (
                    (c[1] - a[1]) * (px - c[0])
                    + (a[0] - c[0]) * (py - c[1])
                ) / denominator
                weight_c = 1.0 - weight_a - weight_b

                if weight_a < -1e-9 or weight_b < -1e-9 or weight_c < -1e-9:
                    continue

                depth = weight_a * a[2] + weight_b * b[2] + weight_c * c[2]
                if zbuffer.test_and_set(x, y, depth):
                    Rasterizer._set_pixel(target, x, y, color)

    @staticmethod
    def _set_pixel(target: object, x: int, y: int, color: Color) -> None:
        try:
            target.set_at((x, y), color)
        except IndexError:
            pass
