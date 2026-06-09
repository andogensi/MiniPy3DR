"""Python wrapper for the native C++ rasterizer."""

from __future__ import annotations

from collections.abc import Sequence

from minipy3dr.core.material import Color


ScreenVertex = tuple[float, float, float]
NativeTriangle = tuple[ScreenVertex, ScreenVertex, ScreenVertex, Color]

try:
    from minipy3dr._native import NativeFrameBuffer as _NativeFrameBuffer
except ImportError as exc:
    _IMPORT_ERROR: ImportError | None = exc
    _NativeFrameBuffer = None
else:
    _IMPORT_ERROR = None


def is_native_available() -> bool:
    return _NativeFrameBuffer is not None


class NativeFrameBuffer:
    def __init__(self, width: int, height: int, background: Color) -> None:
        if _NativeFrameBuffer is None:
            raise RuntimeError("native rasterizer is not built") from _IMPORT_ERROR
        self.width = width
        self.height = height
        self._buffer = _NativeFrameBuffer(width, height, background)
        self._surface: object | None = None

    def clear(self, background: Color) -> None:
        self._buffer.clear(background)

    def fill_triangle(
        self,
        a: ScreenVertex,
        b: ScreenVertex,
        c: ScreenVertex,
        color: Color,
    ) -> None:
        self._buffer.fill_triangle(a, b, c, color)

    def fill_triangles(self, triangles: Sequence[NativeTriangle]) -> None:
        self._buffer.fill_triangles(triangles)

    def render_scene(
        self,
        vertices: object,
        faces: object,
        mesh_ranges: object,
        mesh_states: object,
        materials: object,
        lights: object,
        view_matrix: object,
        projection_matrix: object,
        background: Color,
        near: float,
        far: float,
        cull_far: float,
        vertical_tan: float,
        horizontal_tan: float,
        enable_culling: bool,
    ) -> None:
        self._buffer.render_scene(
            vertices,
            faces,
            mesh_ranges,
            mesh_states,
            materials,
            lights,
            view_matrix,
            projection_matrix,
            background,
            near,
            far,
            cull_far,
            vertical_tan,
            horizontal_tan,
            enable_culling,
        )

    def get_pixel(self, x: int, y: int) -> Color:
        return self._buffer.get_pixel(x, y)

    def blit_to_surface(self, target: object) -> None:
        import pygame

        if self._surface is None:
            self._surface = pygame.image.frombuffer(self._buffer, (self.width, self.height), "RGB")
        target.blit(self._surface, (0, 0))


__all__ = ["NativeFrameBuffer", "NativeTriangle", "is_native_available"]
