"""Scene container."""

from __future__ import annotations

from dataclasses import dataclass, field

from minipy3dr.core.light import DirectionalLight
from minipy3dr.core.material import Material
from minipy3dr.core.mesh import Mesh


@dataclass
class SceneItem:
    mesh: Mesh
    material: Material


@dataclass
class Scene:
    _items: list[SceneItem] = field(default_factory=list)
    _lights: list[DirectionalLight] = field(default_factory=list)

    def add(self, mesh: Mesh, material: Material | None = None) -> Mesh:
        chosen_material = material or mesh.material or Material()
        mesh.material = chosen_material
        self._items.append(SceneItem(mesh, chosen_material))
        return mesh

    def remove(self, mesh: Mesh) -> bool:
        for index, item in enumerate(self._items):
            if item.mesh is mesh:
                del self._items[index]
                return True
        return False

    def add_light(self, light: DirectionalLight) -> DirectionalLight:
        self._lights.append(light)
        return light

    @property
    def items(self) -> tuple[SceneItem, ...]:
        return tuple(self._items)

    @property
    def lights(self) -> tuple[DirectionalLight, ...]:
        return tuple(self._lights)

    @property
    def objects(self) -> tuple[Mesh, ...]:
        return tuple(item.mesh for item in self._items)
