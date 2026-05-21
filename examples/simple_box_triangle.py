"""Draw a 3D box and a single 3D triangle."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pygame

from minipy3dr import Material, Mesh, PerspectiveCamera, Renderer, Scene
from minipy3dr.math import Vector3


def make_triangle() -> Mesh:
    triangle = Mesh(
        vertices=[
            Vector3(-1.2, -0.9, 0.0),
            Vector3(0.0, 1.1, 0.0),
            Vector3(1.2, -0.9, 0.0),
        ],
        faces=[
            (0, 2, 1),
        ],
    )
    triangle.position = Vector3(1.7, 0.0, -5.0)
    return triangle


def main() -> None:
    pygame.init()
    size = (800, 600)
    screen = pygame.display.set_mode(size)
    pygame.display.set_caption("MiniPy3DR - Simple Box and Triangle")
    clock = pygame.time.Clock()

    renderer = Renderer(size)
    camera = PerspectiveCamera(fov=70, aspect=size[0] / size[1], near=0.1, far=100)

    scene = Scene()

    box = Mesh.cube(size=1.7)
    box.position = Vector3(-1.6, 0.0, -5.0)
    scene.add(box, Material((80, 190, 255)))

    triangle = make_triangle()
    scene.add(triangle, Material((255, 120, 80)))

    while True:
        delta = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_q):
                raise SystemExit

        box.rotation = Vector3(box.rotation.x + delta * 0.8, box.rotation.y + delta * 1.2, 0.0)
        triangle.rotation = Vector3(0.0, triangle.rotation.y - delta * 0.9, 0.0)

        renderer.render(scene, camera, screen, mode="solid_numpy")
        pygame.display.flip()


if __name__ == "__main__":
    main()
