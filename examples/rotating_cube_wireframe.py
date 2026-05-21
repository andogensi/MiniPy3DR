"""Render the v0.1 rotating wireframe cube sample."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pygame

from minipy3dr import Material, Mesh, PerspectiveCamera, Renderer, Scene
from minipy3dr.math import Vector3


def main() -> None:
    pygame.init()
    size = (800, 600)
    screen = pygame.display.set_mode(size)
    pygame.display.set_caption("MiniPy3DR v0.1 - Wireframe Cube")
    clock = pygame.time.Clock()

    renderer = Renderer(size=size)
    scene = Scene()
    camera = PerspectiveCamera(fov=70, aspect=size[0] / size[1], near=0.1, far=1000)

    cube = Mesh.cube(size=2.0)
    cube.position = Vector3(0, 0, -5)
    scene.add(cube, material=Material(color=(120, 220, 255)))

    while True:
        delta = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit

        cube.rotation = Vector3(cube.rotation.x + delta * 0.7, cube.rotation.y + delta, 0)
        renderer.render(scene, camera, target=screen, mode="wireframe")
        pygame.display.flip()


if __name__ == "__main__":
    main()
