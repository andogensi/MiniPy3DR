"""A compact row-major 4x4 matrix implementation."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable

from minipy3dr.math.vector import Vector3, Vector4


Rows = tuple[tuple[float, float, float, float], ...]


@dataclass(frozen=True)
class Matrix4:
    rows: Rows

    def __init__(self, rows: Iterable[Iterable[float]]) -> None:
        normalized = tuple(tuple(float(value) for value in row) for row in rows)
        if len(normalized) != 4 or any(len(row) != 4 for row in normalized):
            raise ValueError("Matrix4 requires exactly 4 rows of 4 values")
        object.__setattr__(self, "rows", normalized)

    def __matmul__(self, other: Matrix4 | Vector4) -> Matrix4 | Vector4:
        if isinstance(other, Matrix4):
            return Matrix4(
                (
                    (
                        sum(self.rows[row][k] * other.rows[k][col] for k in range(4))
                        for col in range(4)
                    )
                    for row in range(4)
                )
            )
        if isinstance(other, Vector4):
            x, y, z, w = other.as_tuple()
            values = (x, y, z, w)
            return Vector4(
                *(sum(self.rows[row][col] * values[col] for col in range(4)) for row in range(4))
            )
        return NotImplemented

    def __getitem__(self, index: int) -> tuple[float, float, float, float]:
        return self.rows[index]

    @staticmethod
    def identity() -> Matrix4:
        return Matrix4(
            (
                (1, 0, 0, 0),
                (0, 1, 0, 0),
                (0, 0, 1, 0),
                (0, 0, 0, 1),
            )
        )

    @staticmethod
    def translation(x: float, y: float, z: float) -> Matrix4:
        return Matrix4(
            (
                (1, 0, 0, x),
                (0, 1, 0, y),
                (0, 0, 1, z),
                (0, 0, 0, 1),
            )
        )

    @staticmethod
    def scale(x: float, y: float, z: float) -> Matrix4:
        return Matrix4(
            (
                (x, 0, 0, 0),
                (0, y, 0, 0),
                (0, 0, z, 0),
                (0, 0, 0, 1),
            )
        )

    @staticmethod
    def rotation_x(radians: float) -> Matrix4:
        c = math.cos(radians)
        s = math.sin(radians)
        return Matrix4(
            (
                (1, 0, 0, 0),
                (0, c, -s, 0),
                (0, s, c, 0),
                (0, 0, 0, 1),
            )
        )

    @staticmethod
    def rotation_y(radians: float) -> Matrix4:
        c = math.cos(radians)
        s = math.sin(radians)
        return Matrix4(
            (
                (c, 0, s, 0),
                (0, 1, 0, 0),
                (-s, 0, c, 0),
                (0, 0, 0, 1),
            )
        )

    @staticmethod
    def rotation_z(radians: float) -> Matrix4:
        c = math.cos(radians)
        s = math.sin(radians)
        return Matrix4(
            (
                (c, -s, 0, 0),
                (s, c, 0, 0),
                (0, 0, 1, 0),
                (0, 0, 0, 1),
            )
        )

    @staticmethod
    def euler_xyz(rotation: Vector3) -> Matrix4:
        return (
            Matrix4.rotation_z(rotation.z)
            @ Matrix4.rotation_y(rotation.y)
            @ Matrix4.rotation_x(rotation.x)
        )

    @staticmethod
    def perspective(fov_degrees: float, aspect: float, near: float, far: float) -> Matrix4:
        if aspect <= 0:
            raise ValueError("aspect must be greater than 0")
        if near <= 0 or far <= near:
            raise ValueError("near must be greater than 0 and far must be greater than near")

        f = 1.0 / math.tan(math.radians(fov_degrees) / 2.0)
        return Matrix4(
            (
                (f / aspect, 0, 0, 0),
                (0, f, 0, 0),
                (0, 0, (far + near) / (near - far), (2 * far * near) / (near - far)),
                (0, 0, -1, 0),
            )
        )

    def transform_point(self, point: Vector3) -> Vector3:
        result = self @ Vector4(point.x, point.y, point.z, 1.0)
        if result.w != 0 and result.w != 1:
            return Vector3(result.x / result.w, result.y / result.w, result.z / result.w)
        return Vector3(result.x, result.y, result.z)

    def transform_direction(self, direction: Vector3) -> Vector3:
        result = self @ Vector4(direction.x, direction.y, direction.z, 0.0)
        return Vector3(result.x, result.y, result.z)
