"""Keyboard camera controls for pygame examples and prototypes."""

from __future__ import annotations

from dataclasses import dataclass

from minipy3dr.core import Camera


@dataclass
class KeyboardCameraController:
    camera: Camera
    move_speed: float = 4.0
    turn_speed: float = 1.6

    def update(self, delta: float, keys: object | None = None) -> None:
        import pygame

        pressed = keys if keys is not None else pygame.key.get_pressed()
        move = self.move_speed * delta
        turn = self.turn_speed * delta

        right = _axis(pressed, pygame.K_d, pygame.K_a) * move
        up = _axis(pressed, pygame.K_e, pygame.K_q) * move
        forward = _axis(pressed, pygame.K_w, pygame.K_s) * move
        self.camera.move_local(right=right, up=up, forward=forward)

        yaw = _axis(pressed, pygame.K_LEFT, pygame.K_RIGHT) * turn
        pitch = _axis(pressed, pygame.K_UP, pygame.K_DOWN) * turn
        self.camera.rotate(pitch=pitch, yaw=yaw)


def _axis(keys: object, positive_key: int, negative_key: int) -> int:
    return int(bool(keys[positive_key])) - int(bool(keys[negative_key]))
