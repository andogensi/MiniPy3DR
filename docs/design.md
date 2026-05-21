# MiniPy3DR 設計案

MiniPy3DR は、Pygame の `Surface` に直接描画する軽量なソフトウェア 3D レンダラーを目指す。
最初のゴールは「Pygame のウィンドウ上に、自前の投影・描画処理で回転する 3D キューブを表示する」こと。

## 目的

- Pygame だけで扱いやすい 3D 描画レイヤーを提供する。
- OpenGL 依存ではなく、3D レンダリングの仕組みが見える構造にする。
- 小さなゲーム、教材、プロトタイプで使える API にする。
- 最初はシンプルに作り、OBJ 読み込み、ライティング、テクスチャへ段階的に拡張する。

## 基本方針

- 描画先は `pygame.Surface`。
- 初期実装はソフトウェアレンダリング。
- メッシュは三角形ポリゴンを基本単位にする。
- API は Pygame のメインループに自然に組み込める形にする。
- 数学処理と描画処理は分離する。
- 最初から巨大なエンジンにはせず、小さく動く単位で育てる。

## 想定 API

```python
import pygame
from minipy3dr import Renderer, Scene, PerspectiveCamera, Mesh, Material

pygame.init()
screen = pygame.display.set_mode((800, 600))

renderer = Renderer(size=(800, 600))
scene = Scene()
camera = PerspectiveCamera(fov=70, aspect=800 / 600, near=0.1, far=1000)

cube = Mesh.cube(size=2.0)
scene.add(cube, material=Material(color=(220, 120, 80)))

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            raise SystemExit

    renderer.render(scene, camera, target=screen)
    pygame.display.flip()
```

## ディレクトリ構成

```text
minipy3dr/
  __init__.py
  math/
    __init__.py
    vector.py
    matrix.py
    transform.py
  core/
    __init__.py
    object3d.py
    scene.py
    camera.py
    mesh.py
    material.py
    light.py
  render/
    __init__.py
    renderer.py
    pipeline.py
    rasterizer.py
    zbuffer.py
    shader.py
  loaders/
    __init__.py
    obj_loader.py
  pygame/
    __init__.py
    surface_target.py
examples/
  rotating_cube_wireframe.py
  rotating_cube_solid.py
  obj_viewer.py
tests/
docs/
  architecture.md
  design.md
```

## モジュール設計

### `minipy3dr.math`

3D 計算の基礎を担当する。

- `Vector2`
- `Vector3`
- `Vector4`
- `Matrix4`
- `Transform`

主な責務:

- ベクトル演算
- 行列演算
- 平行移動、回転、拡大縮小
- ビュー行列と射影行列の生成

### `minipy3dr.core`

3D シーンを構成するデータ構造を担当する。

- `Object3D`
- `Scene`
- `Camera`
- `PerspectiveCamera`
- `Mesh`
- `Material`
- `DirectionalLight`
- `AmbientLight`

主な責務:

- オブジェクトの位置、回転、スケール管理
- メッシュデータ管理
- カメラ設定
- マテリアルとライトの管理

### `minipy3dr.render`

描画処理の本体を担当する。

- `Renderer`
- `Pipeline`
- `Rasterizer`
- `ZBuffer`
- `Shader`

主な責務:

- 3D 座標からスクリーン座標への変換
- バックフェイスカリング
- 三角形の塗りつぶし
- Z バッファによる前後関係の解決
- マテリアルとライトを使った色計算

### `minipy3dr.loaders`

外部ファイル読み込みを担当する。

- `OBJLoader`

主な責務:

- `.obj` ファイルの読み込み
- 頂点、法線、UV、面情報の変換
- `Mesh` への変換

### `minipy3dr.pygame`

Pygame との接続部分を担当する。

- `SurfaceTarget`
- 将来的なイベント補助やデバッグ描画

主な責務:

- `pygame.Surface` へのピクセル描画補助
- 色バッファの転送
- Pygame に依存する処理の隔離

## レンダリングパイプライン

```text
local vertices
  -> world transform
  -> view transform
  -> projection transform
  -> clipping
  -> perspective divide
  -> viewport transform
  -> rasterization
  -> z-buffer test
  -> pygame.Surface
```

初期実装では、クリッピングは簡易対応にしてよい。
まずはカメラ前方の単純なオブジェクトが正しく描画できることを優先する。

## 座標系

内部の 3D 空間は右手座標系を想定する。

```text
X: 右
Y: 上
Z: 奥行き
Camera: -Z 方向を見る
Screen: Pygame に合わせて Y 下向き
```

3D 空間の座標系と Pygame のスクリーン座標系は分けて考える。
ビューポート変換の段階で Y 軸を反転する。

## 初期 MVP

最初の到達点はワイヤーフレームの回転キューブ。

必要な機能:

- `Vector3`
- `Matrix4`
- `Transform`
- `PerspectiveCamera`
- `Mesh.cube()`
- `Renderer.draw_wireframe()`
- `examples/rotating_cube_wireframe.py`

この段階では、面の塗りつぶし、Z バッファ、ライティングはまだ不要。

## フェーズ計画

### Phase 1: 数学とワイヤーフレーム

目標:

- 回転する立方体を線で描画する。

実装:

- ベクトルと行列
- Transform
- PerspectiveCamera
- Mesh
- ワイヤーフレーム描画

成果物:

- `examples/rotating_cube_wireframe.py`

### Phase 2: 面描画と Z バッファ

目標:

- 奥の面が手前の面に隠れる立方体を描画する。

実装:

- 三角形ラスタライザ
- Z バッファ
- バックフェイスカリング
- 単色マテリアル

成果物:

- `examples/rotating_cube_solid.py`

### Phase 3: ライティング

目標:

- 立体感のある簡易レンダリングを行う。

実装:

- `AmbientLight`
- `DirectionalLight`
- 面法線
- フラットシェーディング

### Phase 4: OBJ 読み込み

目標:

- Blender などから出力した `.obj` モデルを表示する。

実装:

- OBJ パーサ
- 頂点法線の読み込み
- 自動中央寄せ
- 自動スケール

成果物:

- `examples/obj_viewer.py`

### Phase 5: テクスチャ

目標:

- UV 付きメッシュに画像を貼る。

実装:

- `Texture`
- UV 補間
- 透視補正付きテクスチャマッピング

### Phase 6: ライブラリ公開準備

目標:

- 外部から使いやすいパッケージにする。

実装:

- `pyproject.toml`
- README
- 型ヒント
- API ドキュメント
- サンプル整理
- テスト整備

## バージョン計画

```text
v0.1
- ワイヤーフレーム描画
- 回転キューブサンプル

v0.2
- 三角形塗りつぶし
- Z バッファ
- 単色マテリアル

v0.3
- カメラ操作
- DirectionalLight
- Flat shading

v0.4
- OBJ 読み込み
- OBJ ビューア

v0.5
- テクスチャ
- UV 対応

v1.0
- API 安定化
- pip install 対応
- ドキュメント整備
```

## テスト方針

数学処理はユニットテストを重視する。

優先してテストする対象:

- ベクトル演算
- 行列の積
- 平行移動
- 回転
- 透視投影
- Z バッファ比較
- OBJ 読み込み

描画結果のテストは、最初は完全一致ではなく以下を確認する。

- 例外なく描画できる
- 描画後にピクセルが変化する
- 深度の前後関係が期待通りになる

## 初期依存関係

```text
Python: 3.10+
pygame: 必須
numpy: 推奨
pytest: テスト用
```

初期実装では NumPy を使う方針が扱いやすい。
ただし、教育目的で内部処理を見せたい場合は、最初だけ純 Python 実装にする選択肢もある。

## 実装上の注意

- 最初から機能を増やしすぎない。
- まずワイヤーフレームを完成させる。
- 次に Z バッファ付きの単色三角形描画へ進む。
- テクスチャは難易度が高いため後半に回す。
- OpenGL 依存にすると設計の方向が変わるため、初期段階では使わない。
- Pygame 依存部分は `minipy3dr.pygame` に閉じ込める。

## 次の作業

1. `pyproject.toml` を作成する。
2. `Vector3` と `Matrix4` を実装する。
3. `PerspectiveCamera` を実装する。
4. `Mesh.cube()` を実装する。
5. `rotating_cube_wireframe.py` を作成する。

bakaa