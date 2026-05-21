"""Rendering pipeline, rasterization, and buffering."""

from minipy3dr.render.rasterizer import Rasterizer
from minipy3dr.render.numpy_rasterizer import NumpyFrameBuffer
from minipy3dr.render.renderer import Renderer
from minipy3dr.render.shader import flat_shade, prepare_lights
from minipy3dr.render.zbuffer import ZBuffer

__all__ = [
    "NumpyFrameBuffer",
    "Rasterizer",
    "Renderer",
    "ZBuffer",
    "flat_shade",
    "prepare_lights",
]
