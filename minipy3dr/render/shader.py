"""Small shading helpers used by the software renderer."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import math

from minipy3dr.core.light import DirectionalLight
from minipy3dr.core.material import Color, Material
from minipy3dr.math import Vector3


@dataclass(frozen=True)
class PreparedDirectionalLight:
    incoming: Vector3
    color_scale: tuple[float, float, float]
    intensity: float


def prepare_lights(lights: Iterable[DirectionalLight]) -> tuple[PreparedDirectionalLight, ...]:
    return tuple(
        PreparedDirectionalLight(
            incoming=-light.direction.normalized(),
            color_scale=(
                _clamp(light.color[0] / 255.0, 0.0, 1.0),
                _clamp(light.color[1] / 255.0, 0.0, 1.0),
                _clamp(light.color[2] / 255.0, 0.0, 1.0),
            ),
            intensity=light.intensity,
        )
        for light in lights
    )


def flat_shade(
    material: Material,
    lights: Iterable[DirectionalLight],
    a: Vector3,
    b: Vector3,
    c: Vector3,
) -> Color:
    """Return one shaded color for a triangle face."""

    return flat_shade_prepared(material, prepare_lights(lights), a, b, c)


def flat_shade_prepared(
    material: Material,
    lights: tuple[PreparedDirectionalLight, ...],
    a: Vector3,
    b: Vector3,
    c: Vector3,
) -> Color:
    """Return one shaded color using lights prepared outside the face loop."""

    if not lights:
        return material.color

    ab_x = b.x - a.x
    ab_y = b.y - a.y
    ab_z = b.z - a.z
    ac_x = c.x - a.x
    ac_y = c.y - a.y
    ac_z = c.z - a.z

    normal_x = ab_y * ac_z - ab_z * ac_y
    normal_y = ab_z * ac_x - ab_x * ac_z
    normal_z = ab_x * ac_y - ab_y * ac_x
    normal_length = normal_x * normal_x + normal_y * normal_y + normal_z * normal_z
    if normal_length == 0:
        return material.color

    normal_scale = 1.0 / math.sqrt(normal_length)
    normal_x *= normal_scale
    normal_y *= normal_scale
    normal_z *= normal_scale

    ambient = material.ambient
    if ambient < 0.0:
        ambient = 0.0
    elif ambient > 1.0:
        ambient = 1.0
    diffuse_scale = 1.0 - ambient
    material_red, material_green, material_blue = material.color
    red = material_red * ambient
    green = material_green * ambient
    blue = material_blue * ambient

    for light in lights:
        strength = max(
            0.0,
            normal_x * light.incoming.x
            + normal_y * light.incoming.y
            + normal_z * light.incoming.z,
        ) * light.intensity
        if strength <= 0:
            continue

        lit = diffuse_scale * strength
        red += material_red * lit * light.color_scale[0]
        green += material_green * lit * light.color_scale[1]
        blue += material_blue * lit * light.color_scale[2]

    if red < 0.0:
        red_channel = 0
    elif red > 255.0:
        red_channel = 255
    else:
        red_channel = int(round(red))

    if green < 0.0:
        green_channel = 0
    elif green > 255.0:
        green_channel = 255
    else:
        green_channel = int(round(green))

    if blue < 0.0:
        blue_channel = 0
    elif blue > 255.0:
        blue_channel = 255
    else:
        blue_channel = int(round(blue))

    return (red_channel, green_channel, blue_channel)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _clamp_channel(value: float) -> int:
    return int(round(_clamp(value, 0.0, 255.0)))
