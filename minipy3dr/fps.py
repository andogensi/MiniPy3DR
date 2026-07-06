"""High-level FPS game toolkit for team development (Feature/GameObject/FPSGame).

pygame製のDOOM風FPSを複数人で分担開発するための高レベルAPI。
3D数学・カメラ操作・当たり判定・弾・パーティクルをすべてこのモジュールが
引き受け、利用者は ``Feature`` を継承した小さなクラスを書くだけでよい。

構成:
    - ``FPSConfig`` : 画面・移動速度・色テーマなどの調整値
    - ``Feature``   : 追加機能の基底クラス(必要なフックだけ上書きする)
    - ``GameObject``: 3D空間に置いたモノ(敵・アイテムなど)のハンドル
    - ``FPSGame``   : ゲーム本体。ASCIIマップからワールドを組み立てて回す

最小の使用例::

    from minipy3dr.fps import Feature, FPSGame

    MAP = [
        "#####",
        "#P..#",
        "#####",
    ]

    game = FPSGame(map_data=MAP, title="My FPS")
    game.run()
"""

from __future__ import annotations

import math
import random
import sys
import traceback
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from minipy3dr.app import MiniPy3DRApp as App
from minipy3dr.core import Mesh
from minipy3dr.math import Vector3

__all__ = ["Color", "FPSConfig", "Feature", "FPSGame", "GameObject", "Player", "XZ"]

Color = tuple[int, int, int]
XZ = tuple[float, float]


def _forward_xz(yaw: float) -> XZ:
    """向き(yaw)から正面方向のXZ単位ベクトルを返す。"""
    return -math.sin(yaw), -math.cos(yaw)


def _right_xz(yaw: float) -> XZ:
    """向き(yaw)から右方向のXZ単位ベクトルを返す。"""
    return math.cos(yaw), -math.sin(yaw)


def _shade(color: Color, factor: float) -> Color:
    """色を明るく(factor>1)または暗く(factor<1)した色を返す。"""
    return (
        max(0, min(255, int(color[0] * factor))),
        max(0, min(255, int(color[1] * factor))),
        max(0, min(255, int(color[2] * factor))),
    )


# ---------------------------------------------------------------------------
# 調整用の設定
# ---------------------------------------------------------------------------
@dataclass
class FPSConfig:
    """FPSGameの調整値。必要な項目だけ上書きしてFPSGameに渡す。"""

    # --- 画面 ---
    screen_size: tuple[int, int] = (960, 600)
    render_scale: float = 0.6  # 3D描画の解像度倍率。重いPCでは下げる(例: 0.5)
    fps: int = 60
    fov: float = 78.0  # 視野角(度)
    background: Color = (10, 9, 12)

    # --- ワールドの寸法 ---
    tile: float = 2.0  # マップ1マスの一辺の長さ
    wall_height: float = 2.4
    floor_y: float = -0.8  # 床のワールドY座標(高さ指定は「床からの高さ」で書ける)
    ceiling_y: float = 1.75
    eye_y: float = 0.45  # プレイヤーの目のワールドY座標

    # --- プレイヤー ---
    player_radius: float = 0.4
    walk_speed: float = 4.2
    sprint_speed: float = 6.0  # Shift押下時の速度
    turn_speed: float = 2.6  # キーボード旋回の速度(ラジアン/秒)
    use_qe_turn: bool = True  # QとEを旋回に使う(リーン等に使うならFalse)
    mouse_look: bool = True  # マウス視点(トラックパッド環境ではFalse推奨)
    mouse_sensitivity: float = 0.003
    pitch_min: float = -0.45  # 見下ろし限界
    pitch_max: float = 0.40  # 見上げ限界

    max_health: int = 100
    start_ammo: int = 40
    max_ammo: int = 99

    # --- 弾 ---
    bullet_speed: float = 24.0
    enemy_bullet_speed: float = 7.5

    # --- 描画の軽量化 ---
    view_distance: float = 24.0  # これより遠いオブジェクトは描画しない

    # --- 見た目のテーマ(ここを変えると雰囲気が変わる) ---
    floor_colors: tuple[Color, Color] = ((42, 42, 44), (52, 48, 43))  # 床の市松模様2色
    ceiling_color: Color = (25, 27, 33)
    wall_colors: tuple[Color, Color] = ((96, 82, 76), (126, 108, 90))  # 壁の交互2色
    wall_trim_color: Color = (48, 45, 48)  # 壁の下端の巾木
    wall_top_colors: tuple[Color, Color] = ((66, 78, 92), (88, 74, 96))  # 壁の上端の帯
    lamp_color: Color = (255, 214, 120)  # 天井ランプの光


# ---------------------------------------------------------------------------
# 利用者が継承する基底クラス
# ---------------------------------------------------------------------------
class Feature:
    """追加機能の基底クラス。使いたいメソッドだけ上書きする。

    どのメソッドも上書きは任意(不要なものは書かなくてよい)。
    ある機能でエラーが起きるとその機能だけ停止し、他の機能と
    ゲーム本体は動き続ける(エラー内容はターミナルに表示される)。
    """

    name: str = ""  # 機能名(エラー表示などに使われる)

    def setup(self, game: "FPSGame") -> None:
        """ゲーム開始時に1回呼ばれる。敵やアイテムの配置はここで行う。"""

    def update(self, game: "FPSGame", dt: float) -> None:
        """毎フレーム呼ばれる。dtは前フレームからの経過秒数。"""

    def on_key_down(self, game: "FPSGame", key: str) -> None:
        """キーが押された瞬間に呼ばれる。keyは "e" や "space" などの名前。"""

    def on_mouse_down(self, game: "FPSGame", button: int) -> None:
        """マウスボタンが押された瞬間に呼ばれる。1=左 2=中 3=右。"""

    def draw_hud(self, game: "FPSGame", screen: Any) -> None:
        """3D描画のあとに毎フレーム呼ばれる。HUD(2D表示)はここに描く。

        基本は game.draw_text() / game.draw_bar() などを使えばよい。
        pygameを直接使いたい場合は screen に描画できる。
        """


# ---------------------------------------------------------------------------
# 3D空間に置かれた「モノ」のハンドル
# ---------------------------------------------------------------------------
class GameObject:
    """3D空間に置かれたモノ(敵・アイテムなど)を動かすためのハンドル。

    - ``obj.x`` / ``obj.z`` : マップ上の位置(代入すると移動する)
    - ``obj.y``            : 床からの高さ(0で床の上)
    - ``obj.yaw``          : 向き(ラジアン)。``look_at()`` で向かせる方が簡単
    - ``obj.data``         : 自由に使える辞書(例: ``obj.data["hp"] = 3``)

    生成には game.spawn_box() / game.spawn_character() などを使う。
    """

    def __init__(
        self,
        game: "FPSGame",
        parts: list[tuple[Mesh, Vector3, Vector3]],
        x: float,
        z: float,
        y: float = 0.0,
        radius: float = 0.35,
        name: str = "",
    ) -> None:
        self._game = game
        self._parts = parts  # (メッシュ, ローカルオフセット, 傾き)の組
        self._x = x
        self._z = z
        self._y = y
        self._yaw = 0.0
        self.radius = radius  # 当たり判定・壁判定に使う半径
        self.name = name
        self.alive = True
        self.data: dict[str, Any] = {}
        self._apply()

    # --- 位置と向き(代入すると即座に見た目へ反映される) ---
    @property
    def x(self) -> float:
        return self._x

    @x.setter
    def x(self, value: float) -> None:
        self._x = value
        self._apply()

    @property
    def z(self) -> float:
        return self._z

    @z.setter
    def z(self, value: float) -> None:
        self._z = value
        self._apply()

    @property
    def y(self) -> float:
        return self._y

    @y.setter
    def y(self, value: float) -> None:
        self._y = value
        self._apply()

    @property
    def yaw(self) -> float:
        return self._yaw

    @yaw.setter
    def yaw(self, value: float) -> None:
        self._yaw = value
        self._apply()

    @property
    def pos(self) -> XZ:
        """(x, z) のタプルを返す。"""
        return self._x, self._z

    def set_position(self, x: float, z: float) -> None:
        """位置を直接指定して移動する(壁を無視する)。"""
        self._x = x
        self._z = z
        self._apply()

    # --- 移動 ---
    def move(self, dx: float, dz: float) -> bool:
        """壁にぶつからない範囲で動かす。少しでも動けたらTrueを返す。

        壁に斜めにぶつかったときは壁に沿ってすべる。
        """
        moved = False
        next_x = self._x + dx
        if not self._game.blocked(next_x, self._z, self.radius, ignore=self):
            self._x = next_x
            moved = True
        next_z = self._z + dz
        if not self._game.blocked(self._x, next_z, self.radius, ignore=self):
            self._z = next_z
            moved = True
        self._apply()
        return moved

    def move_towards(self, x: float, z: float, speed: float, dt: float, face: bool = True) -> bool:
        """指定した座標へ向かって speed の速さで1フレームぶん歩く。

        face=True なら進行方向を自動的に向く。動けたらTrueを返す。
        """
        dx = x - self._x
        dz = z - self._z
        distance = math.hypot(dx, dz)
        if distance < 1e-6:
            return False
        step = min(speed * dt, distance)
        if face:
            self._yaw = math.atan2(-dx, -dz)
        return self.move(dx / distance * step, dz / distance * step)

    def look_at(self, x: float, z: float) -> None:
        """指定した座標の方を向く。"""
        dx = x - self._x
        dz = z - self._z
        if dx or dz:
            self.yaw = math.atan2(-dx, -dz)

    def look_at_player(self) -> None:
        """プレイヤーの方を向く。"""
        self.look_at(self._game.player.x, self._game.player.z)

    def distance_to(self, other: "GameObject | XZ") -> float:
        """相手(GameObjectまたは座標タプル)までのXZ平面での距離。"""
        ox, oz = self._game._pos_of(other)
        return math.hypot(self._x - ox, self._z - oz)

    # --- 見た目 ---
    def set_color(self, color: Color) -> None:
        """全パーツの色を変える(被弾フラッシュなどに便利)。"""
        for mesh, _, _ in self._parts:
            self._game.app.set_color(mesh, color)

    def hide(self) -> None:
        """非表示にする(消すわけではない)。"""
        for mesh, _, _ in self._parts:
            mesh.visible = False

    def show(self) -> None:
        """表示する。"""
        for mesh, _, _ in self._parts:
            mesh.visible = True

    def remove(self) -> None:
        """ワールドから完全に削除する。以後このオブジェクトは使えない。"""
        if not self.alive:
            return
        self.alive = False
        self._game.remove_target(self)
        self._game.remove_obstacle(self)
        for mesh, _, _ in self._parts:
            self._game.app.remove(mesh)
        self._parts.clear()

    # --- 内部処理 ---
    def _apply(self) -> None:
        """x/z/y/yawの値を各パーツのメッシュに反映する。"""
        fx, fz = _forward_xz(self._yaw)
        rx, rz = _right_xz(self._yaw)
        floor_y = self._game.config.floor_y
        for mesh, local, tilt in self._parts:
            mesh.position = Vector3(
                self._x + rx * local.x + fx * local.z,
                floor_y + self._y + local.y,
                self._z + rz * local.x + fz * local.z,
            )
            mesh.rotation = Vector3(tilt.x, self._yaw + tilt.y, tilt.z)


# ---------------------------------------------------------------------------
# プレイヤーの状態
# ---------------------------------------------------------------------------
class Player:
    """プレイヤーの状態。health や ammo は自由に読み書きしてよい。

    位置(x, z)はコアが移動処理をするので読み取り専用。
    """

    def __init__(self, game: "FPSGame") -> None:
        self._game = game
        self.health: int = game.config.max_health
        self.max_health: int = game.config.max_health
        self.ammo: int = game.config.start_ammo
        self.max_ammo: int = game.config.max_ammo

    @property
    def x(self) -> float:
        return self._game.app.camera.position.x

    @property
    def z(self) -> float:
        return self._game.app.camera.position.z

    @property
    def pos(self) -> XZ:
        """(x, z) のタプルを返す。"""
        return self.x, self.z

    @property
    def forward(self) -> XZ:
        """今向いている方向のXZ単位ベクトル。"""
        return _forward_xz(self._game._yaw)


# ---------------------------------------------------------------------------
# 内部でだけ使うデータ
# ---------------------------------------------------------------------------
@dataclass
class _Bullet:
    mesh: Mesh
    velocity: Vector3
    ttl: float
    damage: int


@dataclass
class _Particle:
    mesh: Mesh
    velocity: Vector3
    ttl: float
    life: float
    size: float


@dataclass
class _Target:
    obj: GameObject
    on_hit: Callable[[GameObject, int], None]
    radius: float
    height: float


# ---------------------------------------------------------------------------
# ゲーム本体
# ---------------------------------------------------------------------------
class FPSGame:
    """FPSゲームの本体。各機能には ``game`` という名前で渡ってくる。"""

    def __init__(
        self,
        map_data: list[str],
        features: Sequence[Feature] = (),
        title: str = "FPS",
        size: tuple[int, int] | None = None,
        config: FPSConfig | None = None,
    ) -> None:
        self.config = config if config is not None else FPSConfig()
        cfg = self.config

        # 日本語をprintしたときに、ターミナルの文字コード次第でクラッシュしないようにする
        for stream in (sys.stdout, sys.stderr):
            if hasattr(stream, "reconfigure"):
                try:
                    stream.reconfigure(errors="replace")
                except Exception:
                    pass

        # --- マップの検証(マップを編集してもすぐ気付けるように) ---
        self.map = list(map_data)
        if not self.map:
            raise ValueError("MAPが空です。マップ定義を確認してください。")
        width = len(self.map[0])
        for i, row in enumerate(self.map):
            if len(row) != width:
                raise ValueError(
                    f"MAPの{i + 1}行目の長さ({len(row)})が1行目({width})と違います。"
                    "全ての行を同じ長さにしてください。"
                )
        self.map_w = width
        self.map_h = len(self.map)
        self._origin_x = -((self.map_w - 1) * cfg.tile) / 2.0

        # --- 3D描画エンジン ---
        self.app = App(
            size=size if size is not None else cfg.screen_size,
            title=title,
            render_scale=cfg.render_scale,
            background=cfg.background,
            mode="auto",
            fps=cfg.fps,
            fov=cfg.fov,
            near=0.05,
            far=70,
        )
        self.pygame = self.app.pygame  # pygameを直接使いたい人向け
        self.app.renderer.mesh_cull_distance = cfg.view_distance
        self.app.light(direction=(-0.35, -0.9, -0.45), color=(255, 238, 210), intensity=1.15)
        self.app.light(direction=(0.8, -0.45, 0.2), color=(80, 135, 255), intensity=0.2)

        # --- ゲーム状態 ---
        self.features = list(features)
        self.player = Player(self)
        self.score: int = 0
        self.state: str = "playing"  # "playing" / "win" / "lose"
        self.time: float = 0.0
        self._end_title = ""
        self._end_sub = "ESCキーで終了"

        # --- 内部状態 ---
        self._yaw = 0.0
        self._pitch = 0.0
        self._bob_time = 0.0
        self._flash_color: Color = (255, 255, 255)
        self._flash_strength = 0.0
        self._bullets: list[_Bullet] = []
        self._enemy_bullets: list[_Bullet] = []
        self._particles: list[_Particle] = []
        self._targets: list[_Target] = []
        self._obstacles: list[GameObject] = []
        self._timers: list[list[Any]] = []  # [残り秒数, 関数]
        self._listeners: dict[str, list[Callable[[dict[str, Any]], None]]] = {}
        self._broken: set[Feature] = set()
        self._letter_cells: dict[str, list[XZ]] = {}
        self._font_path = self._find_japanese_font()
        self._font_cache: dict[tuple[int, bool], Any] = {}
        self._text_cache: dict[tuple[str, Color, int, bool], Any] = {}
        self._sound_cache: dict[str, Any] = {}
        self._sound_warned: set[str] = set()

        self._build_world()

    # ------------------------------------------------------------------
    # ゲームの開始と終了
    # ------------------------------------------------------------------
    def run(self) -> None:
        """ゲームを開始する。"""
        if self.config.mouse_look:
            self.pygame.mouse.set_visible(False)
            self.pygame.event.set_grab(True)
            self.pygame.mouse.get_rel()
        for feature in self.features:
            self._call_feature(feature, "setup")
        self.app.run(update=self._update, on_event=self._on_event, overlay=self._overlay)

    def quit(self) -> None:
        """ゲームウィンドウを閉じる。"""
        self.app.stop()

    def win(self, message: str = "MISSION COMPLETE") -> None:
        """勝利状態にする。以後、各機能のupdateは呼ばれなくなる。"""
        if self.state == "playing":
            self.state = "win"
            self._end_title = message
            self.emit("victory", {"message": message})

    def lose(self, message: str = "GAME OVER") -> None:
        """敗北状態にする。以後、各機能のupdateは呼ばれなくなる。"""
        if self.state == "playing":
            self.state = "lose"
            self._end_title = message
            self.emit("game_over", {"message": message})

    # ------------------------------------------------------------------
    # 拡張ポイント(サブクラスで上書きする)
    # ------------------------------------------------------------------
    def update_player_extra(self, dt: float) -> None:
        """毎フレーム、プレイヤーの移動とカメラ更新の後に呼ばれる拡張ポイント。

        ジャンプやリーンなどの追加アクションは、FPSGameのサブクラスで
        このメソッドを上書きして実装する。app.camera.position や
        app.camera.rotation をここで加工してよい(毎フレーム、基本の
        移動処理が位置と回転を設定し直したあとに呼ばれる)。
        """

    def draw_overlay_extra(self) -> None:
        """毎フレーム、機能のdraw_hudの後・照準の前に呼ばれる描画の拡張ポイント。

        コア全体に関わる画面演出(ミッション表示・警告表示など)は、
        サブクラスでこのメソッドを上書きして描く。
        """

    # ------------------------------------------------------------------
    # イベント(機能どうしの連絡手段。相手のファイルをimportしないこと)
    # ------------------------------------------------------------------
    def on(self, event: str, callback: Callable[[dict[str, Any]], None]) -> None:
        """イベントの受信登録。callbackは辞書を1つ受け取る関数。

        例: ``game.on("enemy_defeated", self.on_defeated)``
        """
        self._listeners.setdefault(event, []).append(callback)

    def emit(self, event: str, data: dict[str, Any] | None = None) -> None:
        """イベントを発生させる。登録された全ての受信者に届く。

        例: ``game.emit("door_opened", {"x": 4.0, "z": -6.0})``
        """
        payload = data if data is not None else {}
        for callback in list(self._listeners.get(event, [])):
            try:
                callback(payload)
            except Exception:
                print(f"[fps] イベント '{event}' の受信処理でエラー:")
                traceback.print_exc()

    def after(self, seconds: float, callback: Callable[[], None]) -> None:
        """指定秒数後に関数を1回呼ぶ(リスポーンやドアの自動閉鎖などに)。"""
        self._timers.append([seconds, callback])

    # ------------------------------------------------------------------
    # マップの問い合わせ
    # ------------------------------------------------------------------
    def find_cells(self, letter: str) -> list[XZ]:
        """マップ上で指定した文字が置かれたマスの座標(x, z)を全て返す。"""
        return list(self._letter_cells.get(letter, []))

    def is_wall(self, x: float, z: float) -> bool:
        """その座標が壁の中(またはマップ外)ならTrue。"""
        row, col = self.world_to_cell(x, z)
        if row < 0 or col < 0 or row >= self.map_h or col >= self.map_w:
            return True
        return self.map[row][col] == "#"

    def blocked(
        self,
        x: float,
        z: float,
        radius: float | None = None,
        ignore: "GameObject | None" = None,
    ) -> bool:
        """半径radiusの体がその座標に立てないならTrue。

        壁と、add_obstacle()で登録された障害物(扉・柱など)の両方を判定する。
        radiusを省略するとプレイヤーの半径を使う。
        """
        if radius is None:
            radius = self.config.player_radius
        for ox in (-radius, radius):
            for oz in (-radius, radius):
                if self.is_wall(x + ox, z + oz):
                    return True
        for obstacle in self._obstacles:
            if obstacle is ignore or not obstacle.alive:
                continue
            if math.hypot(obstacle.x - x, obstacle.z - z) < obstacle.radius + radius:
                return True
        return False

    def can_see(self, a: "GameObject | Player | XZ", b: "GameObject | Player | XZ") -> bool:
        """aからbまでの間に壁がなければTrue(敵の索敵などに使う)。"""
        ax, az = self._pos_of(a)
        bx, bz = self._pos_of(b)
        dx = bx - ax
        dz = bz - az
        distance = math.hypot(dx, dz)
        steps = max(1, int(distance / 0.3))
        for step in range(1, steps):
            t = step / steps
            if self.is_wall(ax + dx * t, az + dz * t):
                return False
        return True

    def distance(self, a: "GameObject | Player | XZ", b: "GameObject | Player | XZ") -> float:
        """2点(または2オブジェクト)間のXZ平面での距離。"""
        ax, az = self._pos_of(a)
        bx, bz = self._pos_of(b)
        return math.hypot(ax - bx, az - bz)

    def distance_to_player(self, target: "GameObject | XZ") -> float:
        """プレイヤーまでの距離。"""
        return self.distance(target, self.player)

    def near_player(self, target: "GameObject | XZ", within: float) -> bool:
        """プレイヤーとの距離がwithin以下ならTrue(アイテム取得判定などに)。"""
        return self.distance_to_player(target) <= within

    def random_open_cell(self) -> XZ:
        """通路(.)のマスをランダムに1つ選んで座標を返す(敵の湧き位置などに)。"""
        cells = self._letter_cells.get(".", [])
        if not cells:
            raise ValueError("MAPに通路(.)がありません。")
        return random.choice(cells)

    def cell_to_world(self, row: int, col: int) -> XZ:
        """マップのマス目(row, col)の中心のワールド座標(x, z)を返す。"""
        return self._origin_x + col * self.config.tile, -row * self.config.tile

    def world_to_cell(self, x: float, z: float) -> tuple[int, int]:
        """ワールド座標がマップのどのマス目(row, col)かを返す(ミニマップ用)。"""
        tile = self.config.tile
        col = math.floor((x - self._origin_x + tile * 0.5) / tile)
        row = math.floor((-z + tile * 0.5) / tile)
        return row, col

    # ------------------------------------------------------------------
    # オブジェクトの生成
    # ------------------------------------------------------------------
    def spawn_box(
        self,
        x: float,
        z: float,
        size: float | tuple[float, float, float] = 0.6,
        y: float = 0.0,
        color: Color = (200, 200, 200),
        ambient: float = 0.4,
        name: str = "",
    ) -> GameObject:
        """箱を1つ置く。sizeは一辺の長さ、または(幅, 高さ, 奥行き)。

        箱は床の上に置かれる(yで持ち上げられる)。
        """
        if isinstance(size, (int, float)):
            dims = (float(size), float(size), float(size))
        else:
            dims = size
        mesh = self.app.cube(position=(0, 0, 0), scale=dims, color=color, ambient=ambient)
        parts = [(mesh, Vector3(0.0, dims[1] / 2.0, 0.0), Vector3())]
        return GameObject(self, parts, x, z, y=y, radius=max(dims[0], dims[2]) / 2.0, name=name)

    def spawn_pickup(
        self,
        x: float,
        z: float,
        color: Color = (74, 220, 92),
        size: float = 0.42,
        name: str = "",
    ) -> GameObject:
        """アイテム用の光る箱を床の少し上に置く。

        取得判定は ``game.near_player(obj, 0.7)`` などで自分の機能側で行う。
        デフォルト実装は簡素な見た目。サブクラスで上書きして作り込める。
        """
        mesh = self.app.cube(
            position=(0, 0, 0),
            scale=(size, size * 0.55, size),
            color=color,
            ambient=0.75,
        )
        parts = [(mesh, Vector3(0.0, 0.0, 0.0), Vector3())]
        return GameObject(self, parts, x, z, y=0.3, radius=size / 2.0, name=name)

    def spawn_character(
        self,
        x: float,
        z: float,
        color: Color = (172, 42, 40),
        head_color: Color | None = None,
        eye_color: Color = (255, 218, 72),
        scale: float = 1.0,
        style: str = "grunt",
        name: str = "",
    ) -> GameObject:
        """人型キャラクターを置く(敵などに使う)。

        デフォルト実装は胴体+頭+目の簡素な見た目で、styleは無視される。
        スタイル別の作り込んだモデルにしたい場合はサブクラスで上書きする。
        ``obj.look_at_player()`` で全身ごとプレイヤーの方を向く。
        """
        if head_color is None:
            head_color = _shade(color, 1.3)
        s = scale
        body = self.app.cube(position=(0, 0, 0), scale=(0.68 * s, 0.9 * s, 0.52 * s), color=color, ambient=0.3)
        head = self.app.cube(position=(0, 0, 0), scale=(0.52 * s, 0.42 * s, 0.48 * s), color=head_color, ambient=0.32)
        eye_l = self.app.cube(position=(0, 0, 0), scale=(0.09 * s, 0.09 * s, 0.05 * s), color=eye_color, ambient=0.95)
        eye_r = self.app.cube(position=(0, 0, 0), scale=(0.09 * s, 0.09 * s, 0.05 * s), color=eye_color, ambient=0.95)
        parts = [
            (body, Vector3(0.0, 0.5 * s, 0.0), Vector3()),
            (head, Vector3(0.0, 1.12 * s, 0.0), Vector3()),
            (eye_l, Vector3(-0.13 * s, 1.18 * s, 0.25 * s), Vector3()),
            (eye_r, Vector3(0.13 * s, 1.18 * s, 0.25 * s), Vector3()),
        ]
        return GameObject(self, parts, x, z, radius=0.36 * s, name=name)

    # ------------------------------------------------------------------
    # 撃つ・撃たれる
    # ------------------------------------------------------------------
    def add_target(
        self,
        obj: GameObject,
        on_hit: Callable[[GameObject, int], None],
        radius: float = 0.55,
        height: float = 1.5,
    ) -> None:
        """objを「プレイヤーの弾が当たる対象」として登録する。

        弾が当たると ``on_hit(obj, damage)`` が呼ばれる。HPの管理や
        倒れたときの処理(obj.remove()など)は呼ばれた側で行う。
        """
        self._targets.append(_Target(obj, on_hit, radius, height))

    def remove_target(self, obj: GameObject) -> None:
        """弾の当たる対象から外す。obj.remove()を呼べば自動で外れる。"""
        self._targets = [t for t in self._targets if t.obj is not obj]

    def add_obstacle(self, obj: GameObject) -> None:
        """objを「通り抜けられない障害物」にする(扉・柱・バリケードなどに)。

        プレイヤーも、move()/move_towards()で動く敵も通れなくなる。
        obj.remove()すると自動で通れるようになる(=扉が開く)。
        """
        if obj not in self._obstacles:
            self._obstacles.append(obj)

    def remove_obstacle(self, obj: GameObject) -> None:
        """通り抜けられない障害物のリストから外す(扉を開けるときなど)。"""
        if obj in self._obstacles:
            self._obstacles.remove(obj)

    def fire_bullet(
        self,
        damage: int = 1,
        speed: float | None = None,
        color: Color = (255, 226, 86),
        spread: float = 0.0,
    ) -> None:
        """プレイヤーの位置から照準方向へ弾を1発撃つ。

        弾の移動・壁や敵への命中はコアが処理する。命中すると登録済み
        ターゲットのon_hitが呼ばれる。spreadを0.03〜0.1にするとブレる
        (ショットガンはspread付きでこれを複数回呼べばよい)。
        弾数(ammo)の管理は武器側の仕事なので、ここでは減らさない。
        """
        if speed is None:
            speed = self.config.bullet_speed
        direction = self.app.camera.forward
        if spread > 0.0:
            direction = Vector3(
                direction.x + random.uniform(-spread, spread),
                direction.y + random.uniform(-spread, spread),
                direction.z + random.uniform(-spread, spread),
            ).normalized()
        start = self.app.camera.position + direction * 0.6 + Vector3(0.0, -0.06, 0.0)
        mesh = self.app.cube(
            position=start.as_tuple(),
            rotation=(self._pitch, self._yaw, 0.0),
            scale=(0.09, 0.09, 0.4),
            color=color,
            ambient=0.85,
        )
        self._bullets.append(_Bullet(mesh, direction * speed, 1.2, damage))
        self.emit("player_shot", {"damage": damage})

    def enemy_fire(
        self,
        source: "GameObject | XZ",
        damage: int = 10,
        speed: float | None = None,
        color: Color = (255, 74, 82),
        height: float = 1.1,
    ) -> None:
        """敵の位置からプレイヤーへ向かう弾を撃つ(敵AI用)。

        弾の移動とプレイヤーへの命中・ダメージ処理はコアが行う。
        """
        if speed is None:
            speed = self.config.enemy_bullet_speed
        sx, sz = self._pos_of(source)
        start = Vector3(sx, self.config.floor_y + height, sz)
        target = self.app.camera.position + Vector3(0.0, -0.08, 0.0)
        direction = (target - start).normalized()
        mesh = self.app.cube(
            position=(start + direction * 0.3).as_tuple(),
            scale=(0.14, 0.14, 0.3),
            color=color,
            ambient=0.9,
        )
        self._enemy_bullets.append(_Bullet(mesh, direction * speed, 2.2, damage))
        self.emit("enemy_shot", {"damage": damage})

    def explode(
        self,
        x: float,
        z: float,
        radius: float = 2.6,
        damage: int = 2,
        player_damage: int = 30,
        color: Color = (255, 150, 50),
    ) -> None:
        """(x, z)で爆発を起こす(爆発する樽・ロケット弾などに)。

        範囲内の登録済みターゲット全員のon_hitをdamageで呼び、プレイヤーには
        距離に応じて最大player_damageのダメージを与える。演出(パーティクル・
        フラッシュ)込み。"explosion" イベントも発信される。
        """
        self.spawn_particles(x, 0.8, z, color=color, count=24, speed=5.0, ttl=0.5, size=0.14)
        self.spawn_particles(x, 0.4, z, color=(255, 228, 90), count=10, speed=3.0, ttl=0.35, size=0.1)
        self.flash((255, 180, 80), 0.35)

        player_distance = self.distance((x, z), self.player)
        if player_distance < radius:
            self.damage_player(int(player_damage * (1.0 - player_distance / radius)))

        for target in list(self._targets):
            if math.hypot(target.obj.x - x, target.obj.z - z) <= radius:
                try:
                    target.on_hit(target.obj, damage)
                except Exception:
                    print("[fps] 爆発によるon_hit処理でエラー:")
                    traceback.print_exc()

        self.emit("explosion", {"x": x, "z": z, "radius": radius, "damage": damage})

    def aim_target(self, max_distance: float = 20.0) -> GameObject | None:
        """照準(画面中央)の先にいるターゲットを返す。いなければNone。

        撃つ前の照準判定や、レーザー系の即着弾(ヒットスキャン)武器に使える。
        """
        direction = self.app.camera.forward
        position = self.app.camera.position
        steps = int(max_distance / 0.18)
        for step in range(1, steps):
            point = position + direction * (step * 0.18)
            if self.is_wall(point.x, point.z):
                return None
            for target in self._targets:
                base_y = self.config.floor_y + target.obj.y
                if (
                    math.hypot(point.x - target.obj.x, point.z - target.obj.z) < target.radius
                    and base_y <= point.y <= base_y + target.height
                ):
                    return target.obj
        return None

    # ------------------------------------------------------------------
    # プレイヤーへの作用
    # ------------------------------------------------------------------
    def damage_player(self, amount: int) -> None:
        """プレイヤーにダメージを与える。HPが0になると自動で敗北する。"""
        if self.state != "playing":
            return
        self.player.health = max(0, self.player.health - amount)
        self.flash((210, 30, 30), 0.55)
        self.emit("player_damaged", {"amount": amount})
        if self.player.health <= 0:
            self.lose("YOU DIED")

    def heal_player(self, amount: int) -> None:
        """プレイヤーを回復する(最大HPは超えない)。"""
        self.player.health = min(self.player.max_health, self.player.health + amount)
        self.flash((60, 200, 90), 0.25)
        self.emit("player_healed", {"amount": amount})

    def flash(self, color: Color, strength: float = 0.5) -> None:
        """画面全体を一瞬光らせる(ダメージ・回復・爆発の演出に)。"""
        self._flash_color = color
        self._flash_strength = max(self._flash_strength, min(1.0, strength))

    # ------------------------------------------------------------------
    # 演出
    # ------------------------------------------------------------------
    def spawn_particles(
        self,
        x: float,
        y: float,
        z: float,
        color: Color = (255, 180, 60),
        count: int = 8,
        speed: float = 3.0,
        ttl: float = 0.4,
        size: float = 0.1,
    ) -> None:
        """(x, z)の床から高さyの位置に火花を散らす。動きはコアが処理する。"""
        world_y = self.config.floor_y + y
        for _ in range(count):
            if len(self._particles) > 80:
                old = self._particles.pop(0)
                self.app.remove(old.mesh)
            velocity = Vector3(
                random.uniform(-speed, speed),
                random.uniform(0.5, speed),
                random.uniform(-speed, speed),
            )
            mesh = self.app.cube(position=(x, world_y, z), scale=(size, size, size), color=color, ambient=0.9)
            life = ttl * random.uniform(0.7, 1.0)
            self._particles.append(_Particle(mesh, velocity, life, life, size))

    # ------------------------------------------------------------------
    # 音
    # ------------------------------------------------------------------
    def play_sound(self, path: str, volume: float = 1.0) -> None:
        """効果音を1回鳴らす。ファイルは読み込み結果がキャッシュされる。"""
        pg = self.pygame
        try:
            if not pg.mixer.get_init():
                pg.mixer.init()
            sound = self._sound_cache.get(path)
            if sound is None:
                sound = pg.mixer.Sound(path)
                self._sound_cache[path] = sound
            sound.set_volume(volume)
            sound.play()
        except Exception as exc:
            if path not in self._sound_warned:
                self._sound_warned.add(path)
                print(f"[fps] 効果音を再生できません: {path} ({exc})")

    def play_bgm(self, path: str, volume: float = 0.6, loop: bool = True) -> None:
        """BGMを流す。loop=Trueで無限ループ。"""
        pg = self.pygame
        try:
            if not pg.mixer.get_init():
                pg.mixer.init()
            pg.mixer.music.load(path)
            pg.mixer.music.set_volume(volume)
            pg.mixer.music.play(loops=-1 if loop else 0)
        except Exception as exc:
            if path not in self._sound_warned:
                self._sound_warned.add(path)
                print(f"[fps] BGMを再生できません: {path} ({exc})")

    def stop_bgm(self) -> None:
        """BGMを止める。"""
        try:
            self.pygame.mixer.music.stop()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # HUD描画(draw_hudの中で使う。座標は画面ピクセル)
    # ------------------------------------------------------------------
    @property
    def width(self) -> int:
        """画面の幅(ピクセル)。"""
        return self.app.size[0]

    @property
    def height(self) -> int:
        """画面の高さ(ピクセル)。"""
        return self.app.size[1]

    def draw_text(
        self,
        text: str,
        x: int,
        y: int,
        size: int = 24,
        color: Color = (240, 244, 255),
        center: bool = False,
        bold: bool = False,
    ) -> None:
        """日本語対応のテキスト表示。center=Trueで(x, y)が中心になる。"""
        surface = self._text_surface(text, color, size, bold)
        if center:
            rect = surface.get_rect(center=(x, y))
            self.app.screen.blit(surface, rect)
        else:
            self.app.screen.blit(surface, (x, y))

    def draw_bar(
        self,
        x: int,
        y: int,
        value: float,
        max_value: float,
        color: Color,
        label: str = "",
        width: int = 180,
        height: int = 16,
    ) -> None:
        """ゲージ(HPバーなど)を描く。labelを渡すとバーの上に表示される。"""
        draw = self.pygame.draw
        if label:
            self.draw_text(f"{label} {int(value)}", x, y - 26, size=20)
        draw.rect(self.app.screen, (22, 22, 25), (x, y, width, height), border_radius=3)
        if max_value > 0:
            fill = max(0, min(width - 4, int((width - 4) * value / max_value)))
            draw.rect(self.app.screen, color, (x + 2, y + 2, fill, height - 4), border_radius=2)

    def draw_rect(self, x: int, y: int, w: int, h: int, color: Color) -> None:
        """塗りつぶした長方形を描く(ミニマップなどに)。"""
        self.pygame.draw.rect(self.app.screen, color, (x, y, w, h))

    def draw_circle(self, x: int, y: int, radius: int, color: Color) -> None:
        """塗りつぶした円を描く。"""
        self.pygame.draw.circle(self.app.screen, color, (x, y), radius)

    # ------------------------------------------------------------------
    # 内部処理
    # ------------------------------------------------------------------
    def _pos_of(self, target: "GameObject | Player | XZ") -> XZ:
        if isinstance(target, (tuple, list)):
            return float(target[0]), float(target[1])
        return target.x, target.z

    def _build_world(self) -> None:
        """マップ文字列から床・天井・壁・照明を組み立てる。"""
        player_cell: XZ | None = None
        for row, line in enumerate(self.map):
            for col, cell in enumerate(line):
                x, z = self.cell_to_world(row, col)
                if cell == "#":
                    if self._has_open_neighbor(row, col):
                        self.build_wall(row, col, x, z)
                    continue

                self.build_floor_and_ceiling(row, col, x, z)
                if cell == "P":
                    player_cell = (x, z)
                    self._letter_cells.setdefault(".", []).append((x, z))
                    continue
                self._letter_cells.setdefault(cell, []).append((x, z))

        if player_cell is None:
            raise ValueError("MAPにプレイヤー開始位置 P がありません。")
        self.app.camera.position = Vector3(player_cell[0], self.config.eye_y, player_cell[1])
        self.app.camera.rotation = Vector3(0.0, 0.0, 0.0)

    def build_wall(self, row: int, col: int, x: float, z: float) -> None:
        """壁1マスぶんを組み立てる。サブクラスで上書きして見た目を作り込める。"""
        cfg = self.config
        self.app.cube(
            position=(x, cfg.floor_y + cfg.wall_height * 0.5, z),
            scale=(cfg.tile, cfg.wall_height, cfg.tile),
            color=cfg.wall_colors[(row + col) % 2],
            ambient=0.28,
        )

    def build_floor_and_ceiling(self, row: int, col: int, x: float, z: float) -> None:
        """床と天井1マスぶんを組み立てる。サブクラスで上書きして装飾を足せる。"""
        cfg = self.config
        self.app.cube(
            position=(x, cfg.floor_y - 0.04, z),
            scale=(cfg.tile, 0.08, cfg.tile),
            color=cfg.floor_colors[(row + col) % 2],
            ambient=0.4,
        )
        self.app.cube(
            position=(x, cfg.ceiling_y + 0.04, z),
            scale=(cfg.tile, 0.08, cfg.tile),
            color=cfg.ceiling_color,
            ambient=0.32,
        )

    def _has_open_neighbor(self, row: int, col: int) -> bool:
        """周囲8マスに通路があるか(完全に埋まった壁は描画しない軽量化)。"""
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                r, c = row + dr, col + dc
                if 0 <= r < self.map_h and 0 <= c < self.map_w and self.map[r][c] != "#":
                    return True
        return False

    def _call_feature(self, feature: Feature, method_name: str, *args: Any) -> None:
        """機能のフックを呼ぶ。エラーが起きたらその機能だけ止める。"""
        if feature in self._broken:
            return
        try:
            getattr(feature, method_name)(self, *args)
        except Exception:
            label = feature.name or type(feature).__name__
            print(f"[fps] 機能「{label}」の {method_name}() でエラーが発生したため、この機能を停止します:")
            traceback.print_exc()
            self._broken.add(feature)

    # --- メインループ ---
    def _update(self, app: App, dt: float) -> None:
        self.time += dt
        self._flash_strength = max(0.0, self._flash_strength - dt * 2.2)
        self._run_timers(dt)

        if self.state == "playing":
            self._update_player(dt)
            for feature in self.features:
                self._call_feature(feature, "update", dt)
            self._update_bullets(dt)
            self._update_enemy_bullets(dt)
        self._update_particles(dt)

    def _on_event(self, event: Any, app: App) -> None:
        pg = self.pygame
        if event.type == pg.KEYDOWN:
            key_name = pg.key.name(event.key)
            for feature in self.features:
                self._call_feature(feature, "on_key_down", key_name)
        elif event.type == pg.MOUSEBUTTONDOWN:
            for feature in self.features:
                self._call_feature(feature, "on_mouse_down", event.button)

    def _overlay(self, app: App) -> None:
        pg = self.pygame
        if self._flash_strength > 0.0:
            surface = pg.Surface(self.app.size, pg.SRCALPHA)
            r, g, b = self._flash_color
            surface.fill((r, g, b, int(130 * min(1.0, self._flash_strength))))
            self.app.screen.blit(surface, (0, 0))

        for feature in self.features:
            self._call_feature(feature, "draw_hud", self.app.screen)

        self.draw_overlay_extra()
        self.draw_crosshair()

        if self.state != "playing":
            self.draw_end_screen()

    def draw_end_screen(self) -> None:
        """勝敗が決まったときの画面表示。サブクラスで上書きして演出を足せる。"""
        color = (255, 228, 90) if self.state == "win" else (230, 48, 40)
        self.draw_text(self._end_title, self.width // 2, self.height // 2 - 30, size=52, color=color, center=True, bold=True)
        self.draw_text(self._end_sub, self.width // 2, self.height // 2 + 30, size=24, center=True)

    def draw_crosshair(self) -> None:
        """画面中央の照準。サブクラスで上書きして見た目を変えられる。"""
        draw = self.pygame.draw
        cx, cy = self.width // 2, self.height // 2
        color = (238, 235, 210)
        for (x0, y0, x1, y1) in (
            (cx - 14, cy, cx - 5, cy),
            (cx + 5, cy, cx + 14, cy),
            (cx, cy - 14, cx, cy - 5),
            (cx, cy + 5, cx, cy + 14),
        ):
            draw.line(self.app.screen, color, (x0, y0), (x1, y1), 2)

    def _run_timers(self, dt: float) -> None:
        for timer in self._timers[:]:
            timer[0] -= dt
            if timer[0] <= 0.0:
                self._timers.remove(timer)
                try:
                    timer[1]()
                except Exception:
                    print("[fps] after()で登録された処理でエラー:")
                    traceback.print_exc()

    def _update_player(self, dt: float) -> None:
        """WASD移動+マウス/キー視点。壁ずり移動と歩き揺れもここで処理。"""
        app = self.app
        cfg = self.config
        if cfg.mouse_look:
            mouse_dx, mouse_dy = self.pygame.mouse.get_rel()
            self._yaw -= mouse_dx * cfg.mouse_sensitivity
            self._pitch = max(
                cfg.pitch_min,
                min(cfg.pitch_max, self._pitch - mouse_dy * cfg.mouse_sensitivity),
            )
        if app.key("left") or (cfg.use_qe_turn and app.key("q")):
            self._yaw += cfg.turn_speed * dt
        if app.key("right") or (cfg.use_qe_turn and app.key("e")):
            self._yaw -= cfg.turn_speed * dt

        fx, fz = _forward_xz(self._yaw)
        rx, rz = _right_xz(self._yaw)
        move_x = move_z = 0.0
        if app.key("w") or app.key("up"):
            move_x += fx
            move_z += fz
        if app.key("s") or app.key("down"):
            move_x -= fx
            move_z -= fz
        if app.key("a"):
            move_x -= rx
            move_z -= rz
        if app.key("d"):
            move_x += rx
            move_z += rz

        length = math.hypot(move_x, move_z)
        moving = length > 0.001
        if moving:
            sprint = app.key("lshift") or app.key("rshift")
            speed = cfg.sprint_speed if sprint else cfg.walk_speed
            move_x = move_x / length * speed * dt
            move_z = move_z / length * speed * dt

            position = app.camera.position
            next_x = position.x + move_x
            if not self.blocked(next_x, position.z):
                position = Vector3(next_x, position.y, position.z)
            next_z = position.z + move_z
            if not self.blocked(position.x, next_z):
                position = Vector3(position.x, position.y, next_z)
            app.camera.position = position

        self._bob_time += dt * (8.0 if moving else 2.0)
        bob = math.sin(self._bob_time) * (0.035 if moving else 0.01)
        app.camera.position = Vector3(app.camera.position.x, cfg.eye_y + bob, app.camera.position.z)
        app.camera.rotation = Vector3(self._pitch, self._yaw, 0.0)

        self.update_player_extra(dt)

    def _projectile_hits_world(self, position: Vector3, radius: float) -> bool:
        if position.y <= self.config.floor_y + radius or position.y >= self.config.ceiling_y - radius:
            return True
        if self.is_wall(position.x, position.z):
            return True
        # 障害物(遮蔽物・扉など)も弾を止める。高さは data["block_height"] で調整できる。
        # ターゲット登録済みの障害物(樽など)は、命中処理側で当たるのでここでは無視する。
        for obstacle in self._obstacles:
            if not obstacle.alive or any(t.obj is obstacle for t in self._targets):
                continue
            top = self.config.floor_y + obstacle.data.get("block_height", 1.6)
            if position.y <= top and math.hypot(obstacle.x - position.x, obstacle.z - position.z) < obstacle.radius + radius:
                return True
        return False

    def _update_bullets(self, dt: float) -> None:
        """プレイヤーの弾: 壁かターゲットに当たるまで飛ぶ。"""
        floor_y = self.config.floor_y
        for bullet in self._bullets[:]:
            bullet.ttl -= dt
            position = bullet.mesh.position + bullet.velocity * dt
            bullet.mesh.position = position

            if bullet.ttl <= 0.0 or self._projectile_hits_world(position, 0.08):
                self.spawn_particles(position.x, position.y - floor_y, position.z, count=4, ttl=0.2, size=0.07)
                self._remove_bullet(self._bullets, bullet)
                continue

            for target in list(self._targets):
                base_y = floor_y + target.obj.y
                if (
                    math.hypot(position.x - target.obj.x, position.z - target.obj.z) < target.radius
                    and base_y <= position.y <= base_y + target.height
                ):
                    self.spawn_particles(position.x, position.y - floor_y, position.z, count=5, ttl=0.22, size=0.08)
                    self._remove_bullet(self._bullets, bullet)
                    self.emit("target_hit", {"target": target.obj, "damage": bullet.damage})
                    try:
                        target.on_hit(target.obj, bullet.damage)
                    except Exception:
                        print("[fps] ターゲットのon_hit処理でエラー:")
                        traceback.print_exc()
                    break

    def _update_enemy_bullets(self, dt: float) -> None:
        """敵の弾: プレイヤーに当たるとダメージ。"""
        camera = self.app.camera
        floor_y = self.config.floor_y
        for bullet in self._enemy_bullets[:]:
            bullet.ttl -= dt
            position = bullet.mesh.position + bullet.velocity * dt
            bullet.mesh.position = position

            if bullet.ttl <= 0.0 or self._projectile_hits_world(position, 0.1):
                self.spawn_particles(position.x, position.y - floor_y, position.z, count=4, ttl=0.2, size=0.07)
                self._remove_bullet(self._enemy_bullets, bullet)
                continue

            if (position - camera.position).length() < 0.45:
                self._remove_bullet(self._enemy_bullets, bullet)
                self.damage_player(bullet.damage)

    def _remove_bullet(self, bullets: list[_Bullet], bullet: _Bullet) -> None:
        self.app.remove(bullet.mesh)
        if bullet in bullets:
            bullets.remove(bullet)

    def _update_particles(self, dt: float) -> None:
        for particle in self._particles[:]:
            particle.ttl -= dt
            if particle.ttl <= 0.0:
                self.app.remove(particle.mesh)
                self._particles.remove(particle)
                continue
            particle.velocity = Vector3(
                particle.velocity.x * 0.96,
                particle.velocity.y - 5.0 * dt,
                particle.velocity.z * 0.96,
            )
            particle.mesh.position = particle.mesh.position + particle.velocity * dt
            scale = particle.size * max(0.12, particle.ttl / particle.life)
            particle.mesh.scale = Vector3(scale, scale, scale)

    # --- 日本語フォント ---
    def _find_japanese_font(self) -> str | None:
        pg = self.pygame
        for name in ("yu gothic ui", "yu gothic", "meiryo", "msgothic", "noto sans cjk jp"):
            path = pg.font.match_font(name)
            if path:
                return path
        return None

    def _font(self, size: int, bold: bool = False) -> Any:
        key = (size, bold)
        font = self._font_cache.get(key)
        if font is None:
            if self._font_path:
                font = self.pygame.font.Font(self._font_path, size)
                font.set_bold(bold)
            else:
                font = self.pygame.font.SysFont(None, size, bold=bold)
            self._font_cache[key] = font
        return font

    def _text_surface(self, text: str, color: Color, size: int, bold: bool) -> Any:
        key = (text, color, size, bold)
        surface = self._text_cache.get(key)
        if surface is None:
            if len(self._text_cache) > 512:
                self._text_cache.clear()
            surface = self._font(size, bold).render(text, True, color)
            self._text_cache[key] = surface
        return surface
