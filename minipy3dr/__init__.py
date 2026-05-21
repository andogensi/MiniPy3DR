"""MiniPy3DR: a small software 3D renderer for pygame."""

from minipy3dr.app import AppFrame, MiniPy3DRApp, key_code_from_name, vec3
from minipy3dr.core import DirectionalLight, Material, Mesh, PerspectiveCamera, Scene
from minipy3dr.math import Matrix4, Transform, Vector2, Vector3, Vector4
from minipy3dr.pygame import KeyboardCameraController
from minipy3dr.render import Renderer

__version__ = "0.3.0"

App = MiniPy3DRApp

__all__ = [
    "App",
    "AppFrame",
    "DirectionalLight",
    "KeyboardCameraController",
    "Matrix4",
    "Material",
    "Mesh",
    "MiniPy3DRApp",
    "PerspectiveCamera",
    "Renderer",
    "Scene",
    "Transform",
    "Vector2",
    "Vector3",
    "Vector4",
    "key_code_from_name",
    "vec3",
]
