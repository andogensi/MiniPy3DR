"""サウンド・演出機能(担当: ここに名前を書く)

「イベントに効果音を割り当てる」土台だけ入れてある。音源ファイルを
assets/ フォルダに置いて SOUNDS のパスを合わせれば鳴り始める。
ファイルが無い間は警告が出るだけでゲームは普通に動く。
"""

from __future__ import annotations

from typing import Any

from game.core import Feature, FPSGame

# ============================ 実装ミッション ============================
# ★の数は難易度の目安。上から順にやるのがおすすめ。アイデア追加は大歓迎。
#
# TODO(★): フリー音源を集めて assets/ に置き、SOUNDSを埋める
#   射撃・命中・撃破・被弾・回復・勝利・敗北あたりが揃うと一気に
#   ゲームらしくなる。mixerの仕組みは授業資料(第5回p.5)を参照。
#
# TODO(★): BGMを流す(setup内のコメントアウトを外す)
#
# TODO(★★): 場面によってBGMを切り替える
#   game.on("player_damaged", ...) で game.player.health を見て、
#   HPが低いときはピンチ用BGMに切り替える。game.play_bgm() は
#   呼ぶたびに曲を差し替えられる。victory/game_overでジングルに変える。
#
# TODO(★★★): 画面演出も担当する
#   勝利時に紙吹雪: game.after(0.2, ...) を数回ずらして
#   game.spawn_particles(game.player.x, 1.5, game.player.z, color=..., count=20)
#   を連発する。敵撃破時に game.flash((255, 255, 255), 0.15) を入れる、
#   タイトルっぽい演出を draw_hud で作る、など音+視覚の両方で盛り上げる。
# ======================================================================

# イベント名 → 鳴らす音源ファイル(assets/ に置いてから書き換える)
SOUNDS: dict[str, str] = {
    "player_shot": "assets/shot.wav",
    "target_hit": "assets/hit.wav",
    "enemy_defeated": "assets/explosion.wav",
    "player_damaged": "assets/hurt.wav",
    "player_healed": "assets/heal.wav",
    "item_picked": "assets/pickup.wav",
    "empty_click": "assets/click.wav",
    "victory": "assets/win.wav",
    "game_over": "assets/lose.wav",
}


class Sound(Feature):
    """コアや他機能が発信するイベントに効果音を割り当てる。"""

    name = "サウンド・演出"

    def setup(self, game: FPSGame) -> None:
        for event, path in SOUNDS.items():
            # p=path でループ変数を固定するのがコツ(Pythonのよくある罠)
            game.on(event, lambda data, p=path: game.play_sound(p, volume=0.8))
        # game.play_bgm("assets/bgm.mp3", volume=0.5)  # BGMを置いたら有効化
