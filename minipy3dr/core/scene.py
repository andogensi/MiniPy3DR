"""Scene container."""

from __future__ import annotations

from dataclasses import dataclass, field

from minipy3dr.core.material import Material
from minipy3dr.core.mesh import Mesh


@dataclass
class SceneItem:
    mesh: Mesh
    material: Material


@dataclass
class Scene:
    _items: list[SceneItem] = field(default_factory=list)

    def add(self, mesh: Mesh, material: Material | None = None) -> Mesh:
        chosen_material = material or mesh.material or Material()
        mesh.material = chosen_material
        self._items.append(SceneItem(mesh, chosen_material))
        return mesh

    @property
    def items(self) -> tuple[SceneItem, ...]:
        return tuple(self._items)

    @property
    def objects(self) -> tuple[Mesh, ...]:
        return tuple(item.mesh for item in self._items)
