# uv で MiniPy3DR を使う

MiniPy3DR は標準の `pyproject.toml` に対応しているので、`uv` でも使えます。

## GitHub からインストール

```powershell
uv pip install "git+https://github.com/andogensi/MiniPy3DR.git"
```

タグで固定する場合:

```powershell
uv pip install "git+https://github.com/andogensi/MiniPy3DR.git@v0.4.1"
```

## ローカル開発

```powershell
cd D:\Private_D\PROJECT\MiniPy3DR
uv pip install -e .
```

開発用依存関係も入れる場合:

```powershell
uv pip install -e ".[dev]"
```

## 動作確認

```powershell
uv run python -c "from minipy3dr import App; print(App)"
```

## サンプル実行

```powershell
uv run python examples\beginner_01_cube.py
uv run python examples\beginner_02_keyboard.py
uv run python examples\beginner_03_collect_game.py
```

## wheel ビルド

```powershell
uv pip install -e ".[dev]"
uv run python -m build
```

## 注意

このリポジトリ側で特別な uv 専用設定は不要です。
`pip` と `uv pip` の両方で同じ `pyproject.toml` を使います。
