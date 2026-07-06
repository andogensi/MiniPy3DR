"""HUD機能(担当: ここに名前を書く)

「HPバー・弾数・スコア・操作説明の表示」最小の土台だけ入れてある。
下の【実装ミッション】を参考に、自分のHUDに育てること。
3Dの知識は不要で、pygameの2D描画だけで完結する担当。
"""

from __future__ import annotations

from typing import Any

from game.core import Feature, FPSGame

# ============================ 実装ミッション ============================
# ★の数は難易度の目安。上から順にやるのがおすすめ。アイデア追加は大歓迎。
#
# TODO(★): HPバーの色を残量で変える
#   50以下で黄色、25以下で赤。点滅は int(game.time * 4) % 2 == 0 の
#   ときだけ描く、で作れる。
#
# TODO(★★): 撃破ログ・コンボ表示
#   game.on("enemy_defeated", ...) で受け取って「+100」を数秒間表示する。
#   表示の残り時間は self.log_timer を update() で減らして管理する。
#
# TODO(★★★): ミニマップ
#   game.map が文字のリスト(game.map[row][col] で1マス)。
#   1マスを8ピクセルの四角(game.draw_rect)として右上に描く。
#   プレイヤーのいるマスは row, col = game.world_to_cell(game.player.x,
#   game.player.z) で求まる。敵の位置も出したいときは、敵担当に
#   「位置リストをイベントで発信して」と相談する(他人のファイルを
#   importするのは禁止)。
#
# TODO(★★★): 照準の先の敵の情報表示
#   target = game.aim_target() がNoneでなければ、画面中央の少し上に
#   名前(target.name)やHP(target.data.get("hp"))を表示する。
# ======================================================================


class Hud(Feature):
    """画面左上に基本情報、下に操作説明を表示する。"""

    name = "HUD"

    def setup(self, game: FPSGame) -> None:
        self.kills = 0
        # 敵担当のファイルをimportしなくても、イベント経由で撃破数を知れる
        game.on("enemy_defeated", self.on_enemy_defeated)

    def on_enemy_defeated(self, data: dict[str, Any]) -> None:
        self.kills += 1

    def draw_hud(self, game: FPSGame, screen: Any) -> None:
        game.draw_bar(20, 44, game.player.health, game.player.max_health, color=(230, 70, 60), label="HP")
        game.draw_bar(20, 96, game.player.ammo, game.player.max_ammo, color=(80, 160, 255), label="弾薬")
        game.draw_text(f"スコア {game.score}", 20, 122, size=22)
        game.draw_text(f"撃破数 {self.kills}", 20, 150, size=22)
        game.draw_text(
            "WASD移動 / Shiftダッシュ / マウス視点 / 左クリック射撃 / ESC終了",
            20,
            game.height - 36,
            size=18,
            color=(160, 168, 180),
        )
