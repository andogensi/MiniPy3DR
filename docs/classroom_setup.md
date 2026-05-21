# MiniPy3DR 授業用セットアップ

`from minipy3dr import App` で始めるための準備です。

## GitHub から入れる場合

GitHub に公開したリポジトリから入れる場合は、次を 1 回だけ実行します。
`OWNER` は自分の GitHub ユーザー名または Organization 名に置き換えてください。

```powershell
python -m pip install "git+https://github.com/OWNER/MiniPy3DR.git"
```

バージョンを固定したい場合は、タグを付けてから次のようにします。

```powershell
python -m pip install "git+https://github.com/OWNER/MiniPy3DR.git@v0.3.0"
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
