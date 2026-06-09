# MiniPy3DR 初心者向け API ガイド

Pygame の授業で 3D 表現を少しだけ使いたい人向けのガイドです。
最初は `Renderer` や `Scene` を直接使わず、`App` だけを使うと簡単です。

## 最初に 1 回だけセットアップ

`from minipy3dr import App` が見つからない場合は、プロジェクトの一番上のフォルダで
次のコマンドを 1 回だけ実行してください。

```powershell
cd D:\Private_D\PROJECT\MiniPy3DR
python -m pip install -e .
```

これで、`examples` フォルダの中に作ったファイルからも次の import が使えます。

```python
from minipy3dr import App
```

## まず覚える 5 つ

```python
from minipy3dr import App

app = App()                 # ウィンドウを作る
cube = app.cube()           # 立方体を作る
app.light()                 # ライトを置く

def update(app, delta):     # 毎フレーム呼ばれる
    app.rotate(cube, y=delta)

app.run(update=update)      # ゲーム開始
```

## 最小プログラム

```python
from minipy3dr import App

app = App(title="はじめての 3D")
cube = app.cube(position=(0, 0, -5), size=2, color=(220, 120, 80))
app.light()


def update(app, delta):
    app.rotate(cube, x=delta * 0.6, y=delta)


app.run(update=update)
```

## 座標の考え方

MiniPy3DR の 3D 座標は次のように考えます。

```text
x: 右がプラス、左がマイナス
y: 上がプラス、下がマイナス
z: 画面の奥がマイナス
```

最初は `z=-5` あたりに置くと見えやすいです。

```python
cube = app.cube(position=(0, 0, -5))
```

## 立方体を作る

```python
cube = app.cube(
    position=(0, 0, -5),
    scale=(1, 1, 1),
    size=2,
    color=(80, 200, 255),
)
```

よく使う引数:

- `position=(x, y, z)`: 場所
- `scale=(x, y, z)`: 横・縦・奥行きの倍率
- `size=2`: 元の大きさ
- `color=(r, g, b)`: 色。0 から 255
- `ambient=0.2`: 影の明るさ

## 箱・球・床・壁を作る

`cube` は正方形の箱、`box` は横・縦・奥行きを指定する箱です。

```python
player = app.box(position=(0, 0, -5), size=(1, 2, 1), color=(80, 200, 255))
coin = app.sphere(position=(2, 0, -5), radius=0.35, color=(255, 220, 80))
floor = app.floor(position=(0, -1.5, -5), width=8, depth=8)
wall = app.wall(position=(0, 0, -9), width=8, height=3)
```

よく使うゲーム用オブジェクトは `actor` にすると、オブジェクト自身に対して動かせます。

```python
player = app.actor("player", position=(0, 0, -5), size=(1, 2, 1), color=(80, 200, 255))


def update(app, delta):
    player.move(x=2 * delta)
    player.rotate(y=delta)
```

複数のパーツを 1 つとして扱いたいときは `group` を使います。

```python
body = app.box(position=(0, 0, -5), size=(1, 1, 1), color=(80, 200, 255))
head = app.sphere(position=(0, 0.9, -5), radius=0.35, color=(240, 220, 180))
player = app.group(body, head, name="player")

player.move(x=1)
player.hide()
player.show()
```

## 動かす

```python
def update(app, delta):
    app.move(cube, x=delta)
```

`delta` は前のフレームからの秒数です。
速さに `delta` をかけると、速い PC でも遅い PC でも近い動きになります。

```python
def update(app, delta):
    speed = 2.5
    app.move(cube, x=speed * delta)
```

`actor` や `group` も同じように `app.move(player, x=...)` で動かせます。

## 消す

弾や敵のように、途中でいらなくなるものは `app.remove(mesh)` で消せます。
消せたときは `True`、すでに消えているときは `False` が返ります。

```python
bullets = []


def update(app, delta):
    for bullet in bullets[:]:
        app.move(bullet, z=-20 * delta)
        if bullet.position.z < -50:
            app.remove(bullet)
            bullets.remove(bullet)
```

`actor` や `group` なら `player.remove()` でも消せます。

## 回す

```python
def update(app, delta):
    app.rotate(cube, x=delta, y=delta * 1.5)
```

角度はラジアンです。
初心者向けには「`delta` くらい足すとゆっくり回る」と覚えれば十分です。

## キー入力

```python
def update(app, delta):
    speed = 3
    if app.key("left"):
        app.move(cube, x=-speed * delta)
    if app.key("right"):
        app.move(cube, x=speed * delta)
    if app.key("up"):
        app.move(cube, y=speed * delta)
    if app.key("down"):
        app.move(cube, y=-speed * delta)
```

よく使うキー名:

- `"left"`, `"right"`, `"up"`, `"down"`
- `"w"`, `"a"`, `"s"`, `"d"`
- `"space"`
- `"escape"`

## 当たり判定と距離

ミニゲームでは `app.overlaps(a, b)` で簡単な当たり判定ができます。
回転は考えない、軽い箱判定です。

```python
if app.overlaps(player, coin):
    coin.set_position((random.uniform(-3, 3), 0, -5))
```

距離を知りたいときは `app.distance(a, b)` を使います。

```python
if app.distance(player, coin) < 1.0:
    score += 1
```

## 文字を出す

```python
def overlay(app):
    app.draw_text("SCORE 100", (20, 20))


app.run(update=update, overlay=overlay)
```

## 授業の進め方

1. `examples/beginner_01_cube.py`
   回る箱を表示します。

2. `examples/beginner_02_keyboard.py`
   キー入力で箱を動かします。

3. `examples/beginner_03_collect_game.py`
   箱を動かして黄色い箱を集める小さなゲームです。

## よくあるエラー

### `ModuleNotFoundError: No module named 'minipy3dr'`

Python が `minipy3dr` の場所を知らない状態です。
プロジェクトの一番上のフォルダで、次を実行してください。

```powershell
python -m pip install -e .
```

または、授業用サンプルをプロジェクトの一番上から次のように実行します。

```powershell
python -m examples.beginner_01_cube
```

### 何も表示されない

`z` が `0` 以上だとカメラの後ろにあります。
まずは `position=(0, 0, -5)` にしてください。

### 動きが速すぎる

`app.move(cube, x=3)` ではなく、`app.move(cube, x=3 * delta)` にします。

### 色が変わらない

色は 0 から 255 の整数です。

```python
color=(255, 0, 0)  # 赤
color=(0, 255, 0)  # 緑
color=(0, 0, 255)  # 青
```

## 中級者になったら

慣れてきたら `Scene`, `Mesh`, `Material`, `Renderer` を直接使うと、
より細かい制御ができます。
授業の最初は `App` API だけで十分です。
