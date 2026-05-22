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

    @staticmethod
    def _from_rows(rows: Rows) -> Matrix4:
        matrix = Matrix4.__new__(Matrix4)
        object.__setattr__(matrix, "rows", rows)
        return matrix

    def __matmul__(self, other: Matrix4 | Vector4) -> Matrix4 | Vector4:
        if isinstance(other, Matrix4):
            a0, a1, a2, a3 = self.rows
            b0, b1, b2, b3 = other.rows
            return Matrix4._from_rows(
                (
                    (
                        a0[0] * b0[0] + a0[1] * b1[0] + a0[2] * b2[0] + a0[3] * b3[0],
                        a0[0] * b0[1] + a0[1] * b1[1] + a0[2] * b2[1] + a0[3] * b3[1],
                        a0[0] * b0[2] + a0[1] * b1[2] + a0[2] * b2[2] + a0[3] * b3[2],
                        a0[0] * b0[3] + a0[1] * b1[3] + a0[2] * b2[3] + a0[3] * b3[3],
                    ),
                    (
                        a1[0] * b0[0] + a1[1] * b1[0] + a1[2] * b2[0] + a1[3] * b3[0],
                        a1[0] * b0[1] + a1[1] * b1[1] + a1[2] * b2[1] + a1[3] * b3[1],
                        a1[0] * b0[2] + a1[1] * b1[2] + a1[2] * b2[2] + a1[3] * b3[2],
                        a1[0] * b0[3] + a1[1] * b1[3] + a1[2] * b2[3] + a1[3] * b3[3],
                    ),
                    (
                        a2[0] * b0[0] + a2[1] * b1[0] + a2[2] * b2[0] + a2[3] * b3[0],
                        a2[0] * b0[1] + a2[1] * b1[1] + a2[2] * b2[1] + a2[3] * b3[1],
                        a2[0] * b0[2] + a2[1] * b1[2] + a2[2] * b2[2] + a2[3] * b3[2],
                        a2[0] * b0[3] + a2[1] * b1[3] + a2[2] * b2[3] + a2[3] * b3[3],
                    ),
                    (
                        a3[0] * b0[0] + a3[1] * b1[0] + a3[2] * b2[0] + a3[3] * b3[0],
                        a3[0] * b0[1] + a3[1] * b1[1] + a3[2] * b2[1] + a3[3] * b3[1],
                        a3[0] * b0[2] + a3[1] * b1[2] + a3[2] * b2[2] + a3[3] * b3[2],
                        a3[0] * b0[3] + a3[1] * b1[3] + a3[2] * b2[3] + a3[3] * b3[3],
                    ),
                )
            )
        if isinstance(other, Vector4):
            x, y, z, w = other.x, other.y, other.z, other.w
            row_0, row_1, row_2, row_3 = self.rows
            return Vector4(
                row_0[0] * x + row_0[1] * y + row_0[2] * z + row_0[3] * w,
                row_1[0] * x + row_1[1] * y + row_1[2] * z + row_1[3] * w,
                row_2[0] * x + row_2[1] * y + row_2[2] * z + row_2[3] * w,
                row_3[0] * x + row_3[1] * y + row_3[2] * z + row_3[3] * w,
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
        x, y, z = point.x, point.y, point.z
        row_0, row_1, row_2, row_3 = self.rows
        result_x = row_0[0] * x + row_0[1] * y + row_0[2] * z + row_0[3]
        result_y = row_1[0] * x + row_1[1] * y + row_1[2] * z + row_1[3]
        result_z = row_2[0] * x + row_2[1] * y + row_2[2] * z + row_2[3]
        result_w = row_3[0] * x + row_3[1] * y + row_3[2] * z + row_3[3]
        if result_w != 0 and result_w != 1:
            inv_w = 1.0 / result_w
            return Vector3(result_x * inv_w, result_y * inv_w, result_z * inv_w)
        return Vector3(result_x, result_y, result_z)

    def transform_direction(self, direction: Vector3) -> Vector3:
        x, y, z = direction.x, direction.y, direction.z
        row_0, row_1, row_2 = self.rows[0], self.rows[1], self.rows[2]
        return Vector3(
            row_0[0] * x + row_0[1] * y + row_0[2] * z,
            row_1[0] * x + row_1[1] * y + row_1[2] * z,
            row_2[0] * x + row_2[1] * y + row_2[2] * z,
        )
