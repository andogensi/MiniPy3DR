# MiniPy3DR Architecture

MiniPy3DR is planned as a lightweight software 3D renderer that draws into a
`pygame.Surface`.

## Initial Modules

- `minipy3dr.math`: vector, matrix, and transform primitives.
- `minipy3dr.core`: scene graph, camera, mesh, material, lights, and objects.
- `minipy3dr.render`: projection pipeline, triangle rasterizer, and z-buffer.
- `minipy3dr.loaders`: OBJ and future asset loaders.
- `minipy3dr.pygame`: pygame-specific target and convenience helpers.

## First Milestone

Render a rotating wireframe cube on a pygame window.

