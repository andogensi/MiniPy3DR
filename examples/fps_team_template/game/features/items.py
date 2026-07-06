"""アイテム機能(担当: ここに名前を書く)

「Hで回復・Aで弾薬が拾える」最小の土台だけ入れてある。
下の【実装ミッション】を参考に、自分のアイテムシステムに育てること。
"""

from __future__ import annotations

from typing import Any

from game.core import Feature, FPSGame, GameObject

# ============================ 実装ミッション ============================
# ★の数は難易度の目安。上から順にやるのがおすすめ。アイデア追加は大歓迎。
#
# TODO(★): アイテムをふわふわ回転させる
#   update() 内で pickup.yaw += dt * 2.0 で回転、
#   pickup.y = 0.3 + math.sin(game.time * 3.0) * 0.08 で上下に揺れる。
#   (ファイル先頭に import math を忘れずに)
#
# TODO(★★): 取ったときの演出強化
#   game.spawn_particles() の色や数を変える、game.flash() を重ねる、
#   game.emit("item_picked", {"kind": ...}) を発信して音担当に知らせる。
#
# TODO(★★): スコアアイテム・レアアイテム
#   新しいマップ文字(例: G=ゴールド)を決めて game/level.py に追記し、
#   取ると game.score が増えるアイテムを追加する。
#
# TODO(★★★): 鍵と扉
#   扉: door = game.spawn_box(x, z, size=(1.9, 2.2, 0.4), color=(150,110,60))
#       game.add_obstacle(door)  ← これでプレイヤーも敵も通れなくなる
#   鍵を取った状態で扉の近く(game.near_player(door, 1.5))でEキーを押したら
#   (on_key_downで key == "e")door.remove() すると扉が開く。
#   マップ文字(例: D=扉, K=鍵)を level.py に追記すること。
#
# TODO(★★★): 時間制限つきパワーアップ
#   例:「30秒間スコア2倍」「一定時間で弾が徐々に回復」など。
#   効果を切るタイマーは game.after(30.0, 効果を戻す関数) で作れる。
# ======================================================================


class Items(Feature):
    """マップのHに回復パック、Aに弾薬パックを置き、触れたら拾えるようにする。"""

    name = "アイテム"

    def setup(self, game: FPSGame) -> None:
        self.game = game
        self.health_packs: list[GameObject] = [
            game.spawn_pickup(x, z, color=(74, 220, 92), name="health")
            for x, z in game.find_cells("H")
        ]
        self.ammo_packs: list[GameObject] = [
            game.spawn_pickup(x, z, color=(85, 172, 255), name="ammo")
            for x, z in game.find_cells("A")
        ]

    def update(self, game: FPSGame, dt: float) -> None:
        for pack in self.health_packs[:]:
            if game.near_player(pack, 0.7) and game.player.health < game.player.max_health:
                game.heal_player(25)
                self._take(pack, self.health_packs)

        for pack in self.ammo_packs[:]:
            if game.near_player(pack, 0.7) and game.player.ammo < game.player.max_ammo:
                game.player.ammo = min(game.player.max_ammo, game.player.ammo + 15)
                game.flash((70, 170, 255), 0.25)
                self._take(pack, self.ammo_packs)

    def _take(self, pack: GameObject, group: list[GameObject]) -> None:
        """アイテムを取ったときの共通処理。"""
        self.game.spawn_particles(pack.x, 0.5, pack.z, color=(240, 240, 240), count=8, speed=2.0)
        self.game.emit("item_picked", {"kind": pack.name})
        pack.remove()
        group.remove(pack)
