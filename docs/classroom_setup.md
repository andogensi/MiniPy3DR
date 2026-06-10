# MiniPy3DR 授業用セットアップ

`from minipy3dr import App` で始めるための準備です。

## 生徒 PC の標準インストール

生徒 PC には Visual Studio Build Tools が入っていない想定なので、
PyPI に置いた prebuilt wheel を入れるのを標準にします。
PowerShell で次を 1 回だけ実行します。

```powershell
python -m pip install minipy3dr
```

pip が今使っている 64-bit Python のバージョンを見て、
`cp310`, `cp311`, `cp312`, `cp313` のうち合う Windows wheel を
PyPI から選んでインストールします。native renderer も入るので、
C++ コンパイラは不要です。

バージョンを固定したい授業では、`==` で指定します。

```powershell
python -m pip install "minipy3dr==0.4.1"
```

native renderer が入っているか確認します。

```powershell
python -c "from minipy3dr.render import is_native_available; print(is_native_available())"
```

## GitHub のソースから入れる場合

先生側の確認や開発では GitHub から直接入れられます。
ただし、この方法はローカル PC で C++ 拡張をビルドしようとするため、
生徒 PC の標準手順にはしません。

```powershell
python -m pip install "git+https://github.com/andogensi/MiniPy3DR.git"
```

`uv` を使う場合:

```powershell
uv pip install "git+https://github.com/andogensi/MiniPy3DR.git"
```

タグで固定する場合:

```powershell
python -m pip install "git+https://github.com/andogensi/MiniPy3DR.git@v0.4.1"
uv pip install "git+https://github.com/andogensi/MiniPy3DR.git@v0.4.1"
```

## ローカル開発時の準備

プロジェクトの一番上のフォルダを開きます。

```powershell
cd D:\Private_D\PROJECT\MiniPy3DR
```

このコマンドを 1 回だけ実行します。

```powershell
python -m pip install -e .
```

`uv` を使う場合:

```powershell
uv pip install -e .
```

成功すると、どのサンプルからでも次の import が使えます。

```python
from minipy3dr import App
```

## 動作確認

```powershell
python -c "from minipy3dr import App; print(App)"
```

エラーが出なければ OK です。

## サンプルの実行

```powershell
python examples\beginner_01_cube.py
python examples\beginner_02_keyboard.py
python examples\beginner_03_collect_game.py
```

## インストールしない場合

インストールしない場合は、プロジェクトの一番上のフォルダから `-m` で実行します。

```powershell
python -m examples.beginner_01_cube
```

ただし、生徒が自分で `examples\test.py` のようなファイルを作る授業では、
editable install しておく方が分かりやすいです。

## よくある原因

`python examples\test.py` のように実行すると、Python はまず `examples` フォルダを探します。
そのため、1 つ上にある `minipy3dr` フォルダを見つけられず、
`ModuleNotFoundError: No module named 'minipy3dr'` になります。

`python -m pip install -e .` は、このプロジェクトの場所を Python に教えるためのコマンドです。
Pygame と NumPy がまだ入っていない場合は、この時に一緒に入ります。

教室の PC がネットにつながらず、Pygame と NumPy はすでに入っている場合だけ、
次のように依存関係のインストールを省略できます。

```powershell
python -m pip install -e . --no-deps
```
