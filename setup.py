from __future__ import annotations

from setuptools import Extension, find_packages, setup
from setuptools.command.build_ext import build_ext


class BuildExt(build_ext):
    def build_extensions(self) -> None:
        for extension in self.extensions:
            if self.compiler.compiler_type == "msvc":
                extension.extra_compile_args = ["/std:c++17", "/O2", "/EHsc"]
            else:
                extension.extra_compile_args = ["-std=c++17", "-O3"]
        super().build_extensions()


setup(
    packages=find_packages(include=["minipy3dr*"]),
    include_package_data=False,
    cmdclass={"build_ext": BuildExt},
    ext_modules=[
        Extension(
            "minipy3dr._native",
            sources=["minipy3dr/native/rasterizer.cpp"],
            language="c++",
        )
    ],
)
