from __future__ import annotations

import os

from setuptools import Extension, find_packages, setup
from setuptools.command.build_ext import build_ext


class BuildExt(build_ext):
    @staticmethod
    def _require_native() -> bool:
        value = os.environ.get("MINIPY3DR_REQUIRE_NATIVE", "")
        return value.lower() in {"1", "true", "yes", "on"}

    def run(self) -> None:
        try:
            super().run()
        except Exception as exc:
            if self._require_native():
                raise
            self._warn_optional_native(exc)

    def build_extensions(self) -> None:
        for extension in self.extensions:
            if self.compiler.compiler_type == "msvc":
                extension.extra_compile_args = ["/std:c++17", "/O2", "/EHsc"]
            else:
                extension.extra_compile_args = ["-std=c++17", "-O3"]
        super().build_extensions()

    def build_extension(self, extension: Extension) -> None:
        try:
            super().build_extension(extension)
        except Exception as exc:
            if self._require_native():
                raise
            self._warn_optional_native(exc)

    def _warn_optional_native(self, exc: Exception) -> None:
        self.warn(
            "native renderer could not be built; installing the Python/NumPy fallback only. "
            "Use a prebuilt wheel for the faster native renderer, or set "
            "MINIPY3DR_REQUIRE_NATIVE=1 to fail on this error."
        )
        self.warn(f"native build error: {exc}")


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
