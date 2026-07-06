"""武器機能(担当: ここに名前を書く)

「左クリックで撃てる+画面に銃が見える」最小の土台だけ入れてある。
下の【実装ミッション】を参考に、自分の武器システムに育てること。
"""

from __future__ import annotations

import math
from typing import Any

from game.core import Feature, FPSGame

# ============================ 実装ミッション ============================
# ★の数は難易度の目安。上から順にやるのがおすすめ。アイデア追加は大歓迎。
#
# TODO(★): 連射クールダウン
#   今はクリック連打=連打ぶん撃ててしまう。self.cooldown を update() で
#   dt ずつ減らし、0以下のときだけ撃てるようにする。
#
# TODO(★★): 押しっぱなしで連射(フルオート)
#   update() 内で game.pygame.mouse.get_pressed()[0] がTrueの間、
#   クールダウンが切れるたびに撃つ。
#
# TODO(★★): リロード
#   on_key_down() で key == "r" のときリロード開始。時間差の処理は
#   game.after(1.2, self.finish_reload) が便利。リロード中は撃てないように。
#
# TODO(★★★): ショットガン
#   1回の発射で game.fire_bullet(damage=1, spread=0.08) を6回呼ぶと散弾になる。
#
# TODO(★★★): 武器切替(1キー/2キー/3キー)
#   武器ごとの性能(連射速度・ダメージ・散弾数)を辞書かクラスにまとめて
#   on_key_down() で切り替える。draw_hud() の銃の見た目も武器ごとに変える。
#
# TODO(★・見た目): 反動とマズルフラッシュの強化
#   撃った瞬間に self.recoil を増やし、draw_hud() の銃の描画位置を
#   下にずらすと反動になる。game.flash() を混ぜると更に派手。
# ======================================================================


class Weapons(Feature):
    """左クリックで弾を1発撃つ。画面下に銃を描く。"""

    name = "武器"

    def setup(self, game: FPSGame) -> None:
        self.muzzle_timer = 0.0  # マズルフラッシュの残り表示時間(秒)

    def update(self, game: FPSGame, dt: float) -> None:
        self.muzzle_timer = max(0.0, self.muzzle_timer - dt)

    def on_mouse_down(self, game: FPSGame, button: int) -> None:
        if button != 1:  # 左クリック以外は無視
            return
        if game.player.ammo <= 0:
            game.emit("empty_click", {})  # 音担当が「カチッ」を鳴らせるように通知
            return
        game.player.ammo -= 1
        game.fire_bullet(damage=1)
        self.muzzle_timer = 0.07

    def draw_hud(self, game: FPSGame, screen: Any) -> None:
        # 画面下中央に銃を描く(四角と多角形の組み合わせ。凝りたい人は自由に改造)
        draw = game.pygame.draw
        cx = game.width // 2
        # 構え揺れ(呼吸のようにゆっくり揺れる)+撃った瞬間の反動で下がる
        sway_x = int(math.sin(game.time * 1.7) * 4)
        sway_y = int(math.cos(game.time * 3.4) * 3)
        kick = int(self.muzzle_timer * 260)
        gx = cx + sway_x
        gy = game.height - 128 + sway_y + kick

        # 腕とグローブ
        draw.polygon(screen, (52, 46, 44), [(gx - 88, gy + 132), (gx - 30, gy + 66), (gx + 30, gy + 66), (gx + 88, gy + 132)])
        draw.rect(screen, (74, 62, 54), (gx - 34, gy + 62, 68, 70), border_radius=8)
        draw.rect(screen, (58, 48, 42), (gx - 34, gy + 62, 68, 12), border_radius=6)  # グローブの締め口
        # フレームとスライド
        draw.rect(screen, (52, 54, 60), (gx - 30, gy - 6, 60, 78), border_radius=6)
        draw.rect(screen, (108, 112, 120), (gx - 24, gy - 18, 48, 62), border_radius=4)
        draw.rect(screen, (76, 80, 88), (gx - 24, gy - 18, 48, 14), border_radius=4)  # スライド上面の影
        draw.rect(screen, (30, 32, 36), (gx + 4, gy - 8, 16, 8), border_radius=2)  # 排莢口
        # 銃身と銃口
        draw.rect(screen, (38, 40, 46), (gx - 10, gy - 34, 20, 22), border_radius=3)
        draw.rect(screen, (14, 14, 16), (gx - 6, gy - 31, 12, 9), border_radius=2)  # 銃口の穴
        # フロントサイトと黄色のアクセント
        draw.rect(screen, (230, 190, 70), (gx - 3, gy - 43, 6, 8))
        draw.rect(screen, (230, 190, 70), (gx - 24, gy + 32, 48, 5))

        if self.muzzle_timer > 0.0:
            flash_y = gy - 40
            draw.polygon(screen, (255, 236, 120), [(gx, flash_y - 48), (gx - 27, flash_y), (gx + 27, flash_y)])
            draw.polygon(screen, (255, 150, 40), [(gx, flash_y - 25), (gx - 14, flash_y), (gx + 14, flash_y)])
            draw.circle(screen, (255, 246, 200), (gx, flash_y - 9), 7)
