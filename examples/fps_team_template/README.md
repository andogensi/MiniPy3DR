# DOOM風FPS チーム開発テンプレート

MiniPy3DR(pygame製の3Dレンダラ)のFPSツールキット `minipy3dr.fps` を使った
チーム開発テンプレート。3Dの数学・当たり判定・弾の処理は全部ライブラリが
やるので、**各メンバーは自分のファイルを1個書くだけ**。

## 実行環境の必要条件

* Python >= 3.10
* pygame >= 2.5
* minipy3dr >= 0.5.0 (`pip install minipy3dr`)

## 実行方法

```
python main.py
```

## フォルダ構成と担当

| 場所 | 内容 | 担当 |
|---|---|---|
| `main.py` | 起動処理 | 代表者 |
| `game/core.py` | 班固有の拡張(追加アクション等)。エンジン本体は`minipy3dr.fps` | 代表者 |
| `game/config.py` | 調整用の設定・色テーマ | 相談の上で変更 |
| `game/level.py` | マップ(文字で描く) | 使う文字を追記してから |
| `game/features/enemies.py` | 敵のAI・種類 | (名前) |
| `game/features/weapons.py` | 武器・射撃 | (名前) |
| `game/features/items.py` | アイテム・鍵と扉 | (名前) |
| `game/features/hud.py` | HUD・ミニマップ | (名前) |
| `game/features/sound.py` | 音・演出 | (名前) |
| `game/features/__init__.py` | 機能の登録リスト | 自分の行だけ |

## 進め方

1. 自分の担当ファイルを開く。**動く最小の土台**と、ファイル冒頭に
   **【実装ミッション】(TODOコメント)** が書いてある
2. ★の少ないミッションから順に実装する。★★★までやれば十分な分量になる。
   ミッションはあくまで例なので、自分のアイデアを足すのは大歓迎
3. こまめに `python main.py` で動作確認 → 自分のブランチにコミット

自分の機能でエラーが起きても**その機能だけ止まり、ゲームは動き続ける**
(エラー内容はターミナルに出るので読んで直すこと)。

各ファイルの土台は「書き方のお手本」を兼ねている。土台のままでは
個人実装として認められないので、**ミッションぶんは必ず自分で書くこと**
(AI生成・コピペは0点+TAの前でコードを説明するデモがある)。

## 機能クラスの書き方

`Feature` を継承して、**使いたいメソッドだけ**上書きする:

| メソッド | いつ呼ばれるか |
|---|---|
| `setup(game)` | ゲーム開始時に1回。敵・アイテムの配置はここ |
| `update(game, dt)` | 毎フレーム。動き・時間経過の処理はここ |
| `on_key_down(game, key)` | キーが押された瞬間。`key`は`"e"`や`"space"` |
| `on_mouse_down(game, button)` | クリックの瞬間。1=左 2=中 3=右 |
| `draw_hud(game, screen)` | 毎フレームの最後。2D表示(バー・文字)はここ |

## `game` でできること(チートシート)

### 配置する
```python
obj = game.spawn_box(x, z, size=0.6, color=(200,200,200))    # 箱
obj = game.spawn_pickup(x, z, color=(74,220,92))             # 補給物資(光るクレート)
obj = game.spawn_character(x, z, color=..., style="grunt")   # 人型キャラ
#   style: "grunt"標準 / "imp"角つき / "brute"大型 / "turret"砲台 / "boss"ボス
game.spawn_particles(x, 高さ, z, color=..., count=8)          # 火花エフェクト
```

### 置いたモノ(GameObject)を動かす
```python
obj.x, obj.z          # 位置(代入で移動)     obj.y   # 床からの高さ
obj.yaw               # 向き(ラジアン)
obj.move(dx, dz)                  # 壁にぶつからないように動く
obj.move_towards(x, z, speed, dt) # 目標へ1フレームぶん歩く(向きも変わる)
obj.look_at_player()              # プレイヤーの方を向く
obj.set_color((255,255,255))      # 色を変える(被弾フラッシュなど)
obj.hide() / obj.show()           # 表示切替
obj.remove()                      # 完全に消す
obj.data["hp"] = 3                # 自由メモ欄(HPやクールダウンを入れる)
```

### 調べる
```python
game.player.x, game.player.z    # プレイヤーの位置
game.player.health / ammo       # HP・弾数(読み書き自由)
game.distance(a, b)             # 距離
game.near_player(obj, 1.0)      # プレイヤーが1.0以内にいるか
game.can_see(obj, game.player)  # 間に壁がないか(索敵)
game.find_cells("H")            # マップの文字Hの位置リスト
game.is_wall(x, z) / game.blocked(x, z)   # 壁・障害物判定
game.world_to_cell(x, z)        # ワールド座標→マス目(row, col)。ミニマップ用
game.cell_to_world(row, col)    # マス目→ワールド座標
game.random_open_cell()         # ランダムな通路の座標
```

### 撃つ・ダメージ・障害物
```python
game.fire_bullet(damage=1, spread=0.0)  # プレイヤーが撃つ(弾数は自分で減らす)
game.add_target(obj, on_hit=関数)        # objを「撃たれる対象」に登録
game.aim_target()                       # 照準の先にいるターゲット(なければNone)
game.enemy_fire(敵obj, damage=10)        # 敵がプレイヤーを狙って撃つ
game.damage_player(10) / game.heal_player(25)
game.explode(x, z, radius=2.6, damage=2)  # 範囲爆発(樽やロケット弾に)
game.add_obstacle(obj)                  # objを通行不能にする(扉・柱に)
game.remove_obstacle(obj)               # 通れるように戻す(obj.remove()でも外れる)
```

### 表示・演出・音
```python
game.draw_text("テキスト", x, y, size=24)     # 日本語OK
game.draw_bar(x, y, 値, 最大値, color, label="HP")
game.draw_rect(...) / game.draw_circle(...)  # ミニマップなどに
game.flash((255,0,0), 0.5)                   # 画面を一瞬光らせる
game.play_sound("assets/shot.wav") / game.play_bgm("assets/bgm.mp3")
```

### ゲーム進行・その他
```python
game.score += 100                 # スコア
game.win("クリア!") / game.lose()  # 勝敗を確定させる
game.after(2.0, 関数)              # 2秒後に関数を1回呼ぶ
game.time                        # ゲーム開始からの秒数
game.width, game.height          # 画面サイズ(HUD用)
```

## イベント(機能どうしの連絡)

**他人のファイルをimportしてはいけない。** かわりにイベントを使う:

```python
game.emit("door_opened", {"x": 4.0})   # 発信(自作イベント名でOK)
game.on("door_opened", self.on_door)   # 受信登録(setup内で)
def on_door(self, data): ...           # dataは辞書
```

コアが自動で発信: `player_shot` / `enemy_shot` / `target_hit` / `explosion` /
`player_damaged` / `player_healed` / `victory` / `game_over`
土台の機能が発信: `enemy_defeated` / `item_picked` / `empty_click`

ベースのギミックとして、マップの `B` に**爆発する樽**(撃つと範囲ダメージ+誘爆)、
`C` に**遮蔽コンテナ**(通れず、弾も防ぐ)が置かれる。実装は core.py。

## マップの編集(game/level.py)

`#`=壁 `.`=通路 `P`=開始位置。それ以外の文字は自由に使える。
新しい文字を使うときは、他の人とかぶらないように `level.py` の
docstringに追記すること。見た目の色テーマは `config.py` で変えられる。

## 採点に関わる注意

* 型ヒント・docstring・コメントは採点対象。土台の書き方に合わせること
* 自分の担当機能は**必ず自分で書く**(AI生成・コピペは0点+デモで説明あり)
* コードを書いたら `python main.py` で動作確認してからコミットする
