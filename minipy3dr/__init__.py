"""MiniPy3DR: a small software 3D renderer for pygame."""

from minipy3dr.core import Material, Mesh, PerspectiveCamera, Scene
from minipy3dr.render import Renderer

__version__ = "0.2.0"

__all__ = [
    "Material",
    "Mesh",
    "PerspectiveCamera",
    "Renderer",
    "Scene",
]
