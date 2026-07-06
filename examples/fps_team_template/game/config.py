"""ゲームの調整用設定(ベース部分)。

数値を変えるだけでゲームの手触りや見た目が変わる。
全項目の一覧とデフォルト値は minipy3dr.fps の FPSConfig を参照
(VSCodeで FPSConfig をCtrl+クリックすると定義に飛べる)。
全員に影響するファイルなので、値を変えるときはグループで相談すること。
"""

from minipy3dr.fps import FPSConfig

CONFIG = FPSConfig(
    # --- 画面 ---
    screen_size=(960, 600),
    render_scale=0.6,  # 動作が重いPCでは 0.5 に下げる
    fov=78.0,  # 視野角(度)
    # --- プレイヤー ---
    walk_speed=4.2,
    sprint_speed=6.0,  # Shift押下時の速度
    mouse_look=True,  # トラックパッド環境ならFalse
    max_health=100,
    start_ammo=40,
    # --- 見た目のテーマ(色を変えると雰囲気が変わる) ---
    floor_colors=((42, 42, 44), (52, 48, 43)),
    wall_colors=((96, 82, 76), (126, 108, 90)),
    lamp_color=(255, 214, 120),
)

# ここから下は代表者(コア担当)の追加定数を書く場所
