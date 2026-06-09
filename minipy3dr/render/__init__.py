"""Rendering pipeline, rasterization, and buffering."""

from minipy3dr.render.native_rasterizer import NativeFrameBuffer, NativeTriangle, is_native_available
from minipy3dr.render.rasterizer import Rasterizer
from minipy3dr.render.numpy_rasterizer import NumpyFrameBuffer
from minipy3dr.render.renderer import Renderer
from minipy3dr.render.shader import flat_shade, prepare_lights
from minipy3dr.render.zbuffer import ZBuffer

__all__ = [
    "NativeFrameBuffer",
    "NativeTriangle",
    "NumpyFrameBuffer",
    "Rasterizer",
    "Renderer",
    "ZBuffer",
    "flat_shade",
    "is_native_available",
    "prepare_lights",
]
