"""敵機能(担当: ここに名前を書く)

「Eの位置に敵が湧く+見えたら追いかけてくる+撃てば倒せる」最小の
土台だけ入れてある。下の【実装ミッション】で自分の敵AIに育てること。
"""

from __future__ import annotations

from game.core import Feature, FPSGame, GameObject

# ============================ 実装ミッション ============================
# ★の数は難易度の目安。上から順にやるのがおすすめ。アイデア追加は大歓迎。
#
# TODO(★): 被弾フラッシュ
#   on_shot() の中で enemy.set_color((255, 255, 255)) で白く光らせて、
#   game.after(0.1, lambda: enemy.set_color((180, 45, 40))) で色を戻す。
#
# TODO(★★): 敵の種類を増やす
#   game.spawn_character(x, z, color=..., style="imp") で見た目が変わる。
#   style: "grunt"(標準) / "imp"(角つき) / "brute"(大型・height=1.8推奨)
#         / "turret"(砲台・height=1.1推奨) / "boss"(大型ボス・height=2.2推奨)
#         (heightはadd_targetの引数)
#   種類ごとに hp・速度・スコアを変える。新しいマップ文字(例: T)を決めて
#   game/level.py に追記し、game.find_cells("T") で配置する。
#
# TODO(★★): 遠距離攻撃
#   プレイヤーが見えていて距離が3〜9のとき、クールダウンごとに
#   game.enemy_fire(enemy, damage=8) で弾を撃つ。
#
# TODO(★★★): 巡回⇔追跡の状態遷移
#   enemy.data["mode"] に "patrol" / "chase" を入れて切り替える。
#   見えたら追跡、見失ったら巡回に戻る。巡回先は game.random_open_cell()。
#
# TODO(★★★): リスポーン/ウェーブ制
#   倒されたら game.after(5.0, ...) で別の場所に再出現させる。
#   その場合「全滅で勝利」は成立しなくなるので、勝利条件も決め直すこと。
# ======================================================================


class Enemies(Feature):
    """マップのEの位置に敵を出す。見えている間だけ追いかけてくる。"""

    name = "敵"

    def setup(self, game: FPSGame) -> None:
        self.game = game  # on_shotコールバックの中で使うため覚えておく
        self.enemies: list[GameObject] = []
        for x, z in game.find_cells("E"):
            enemy = game.spawn_character(x, z, color=(180, 45, 40), style="grunt", name="enemy")
            enemy.data["hp"] = 3
            enemy.data["attack_cooldown"] = 0.0
            game.add_target(enemy, on_hit=self.on_shot)  # プレイヤーの弾が当たるようにする
            self.enemies.append(enemy)

    def update(self, game: FPSGame, dt: float) -> None:
        for enemy in self.enemies:
            enemy.data["attack_cooldown"] = max(0.0, enemy.data["attack_cooldown"] - dt)

            # プレイヤーが見えていて、離れていたら近づく
            if game.can_see(enemy, game.player) and game.distance_to_player(enemy) > 1.0:
                enemy.move_towards(game.player.x, game.player.z, speed=1.4, dt=dt)

            # 密着したら体当たりダメージ
            if game.near_player(enemy, 1.1) and enemy.data["attack_cooldown"] <= 0.0:
                game.damage_player(12)
                enemy.data["attack_cooldown"] = 0.9

    def on_shot(self, enemy: GameObject, damage: int) -> None:
        """プレイヤーの弾が当たったときにコアから呼ばれる。"""
        game = self.game
        enemy.data["hp"] -= damage
        if enemy.data["hp"] > 0:
            return

        # 撃破: 爆発エフェクト → 削除 → スコア加算 → 全滅なら勝利
        game.spawn_particles(enemy.x, 1.0, enemy.z, color=(255, 120, 40), count=16, speed=4.0)
        enemy.remove()
        self.enemies.remove(enemy)
        game.score += 100
        game.emit("enemy_defeated", {"remaining": len(self.enemies)})
        if not self.enemies:
            game.win("EZLOL")
