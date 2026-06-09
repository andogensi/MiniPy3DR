from __future__ import annotations

from types import SimpleNamespace

from minipy3dr import (
    App,
    KeyboardCameraController,
    Material,
    Mesh,
    MiniPy3DRApp,
    AppObject,
    Scene,
    Vector3,
    key_code_from_name,
    vec3,
)


def test_high_level_api_exports_from_top_level_package() -> None:
    assert App is MiniPy3DRApp
    assert AppObject is not None
    assert KeyboardCameraController is not None


def test_vec3_accepts_tuple_and_existing_vector() -> None:
    vector = Vector3(1, 2, 3)

    assert vec3((1, 2, 3)) == vector
    assert vec3(vector) is vector


def test_key_code_from_name_accepts_beginner_aliases() -> None:
    pygame = SimpleNamespace(K_LEFT=1, K_ESCAPE=2, K_SPACE=3)

    assert key_code_from_name(pygame, "left") == 1
    assert key_code_from_name(pygame, "esc") == 2
    assert key_code_from_name(pygame, "space") == 3


def test_scene_remove_deletes_mesh_by_identity() -> None:
    scene = Scene()
    first = scene.add(Mesh.cube(), Material(color=(255, 0, 0)))
    second = scene.add(Mesh.cube(), Material(color=(0, 255, 0)))

    assert scene.remove(Mesh.cube()) is False
    assert scene.objects == (first, second)

    assert scene.remove(first) is True
    assert scene.objects == (second,)


def test_scene_set_material_updates_mesh_and_scene_item() -> None:
    scene = Scene()
    mesh = scene.add(Mesh.cube())
    material = Material(color=(10, 20, 30), ambient=0.4)

    assert scene.set_material(mesh, material) is True
    assert mesh.material == material
    assert scene.items[0].material == material
    assert scene.set_material(Mesh.cube(), material) is False


def test_mesh_sphere_creates_expected_primitive() -> None:
    sphere = Mesh.sphere(radius=2.0, segments=6, rings=4)

    assert len(sphere.vertices) == 20
    assert len(sphere.faces) == 36
    assert sphere.vertices[0] == Vector3(0.0, 2.0, 0.0)
    assert sphere.vertices[-1] == Vector3(0.0, -2.0, 0.0)


def test_app_shape_helpers_can_build_without_opening_pygame_window() -> None:
    app = MiniPy3DRApp.__new__(MiniPy3DRApp)
    app.scene = Scene()

    box = app.box(position=(1, 2, -5), size=(2, 3, 4), color=(1, 2, 3))
    sphere = app.sphere(position=(0, 0, -6), radius=0.5, color=(4, 5, 6))
    floor = app.floor(width=10, depth=12)
    wall = app.wall(axis="z", width=7, height=2)

    assert box.scale == Vector3(2, 3, 4)
    assert sphere.material == Material(color=(4, 5, 6), ambient=0.18)
    assert floor.scale == Vector3(10, 0.1, 12)
    assert wall.scale == Vector3(0.1, 2, 7)
    assert app.scene.objects == (box, sphere, floor, wall)


def test_app_object_groups_move_remove_and_collide() -> None:
    app = MiniPy3DRApp.__new__(MiniPy3DRApp)
    app.scene = Scene()

    body = app.box(position=(0, 0, -5), size=(1, 1, 1), color=(10, 20, 30))
    head = app.sphere(position=(0, 0.9, -5), radius=0.3, color=(30, 40, 50))
    player = app.group(body, head, name="player")
    coin = app.actor("coin", position=(0.4, 0, -5), size=0.3, color=(255, 220, 80))

    assert player.name == "player"
    assert player.overlaps(coin)
    assert app.distance(player, coin) == 0.4

    app.move(player, x=2)
    assert body.position == Vector3(2, 0, -5)
    assert head.position == Vector3(2, 0.9, -5)
    assert not app.overlaps(player, coin)

    app.set_color(player, (90, 100, 110), ambient=0.5)
    assert body.material == Material(color=(90, 100, 110), ambient=0.5)
    assert head.material == Material(color=(90, 100, 110), ambient=0.5)

    assert app.remove(player) is True
    assert app.scene.objects == (coin.mesh,)
