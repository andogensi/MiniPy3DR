# GitHub から pip install する方法

MiniPy3DR は `pyproject.toml` を持っているので、GitHub に push すれば
そのまま `pip install` できます。

## インストールする側

`OWNER` を GitHub のユーザー名または Organization 名に置き換えます。

```powershell
python -m pip install "git+https://github.com/OWNER/MiniPy3DR.git"
```

特定のブランチを入れる場合:

```powershell
python -m pip install "git+https://github.com/OWNER/MiniPy3DR.git@main"
```

授業ではタグで固定するのがおすすめです。

```powershell
python -m pip install "git+https://github.com/OWNER/MiniPy3DR.git@v0.3.0"
```

更新したものを入れ直す場合:

```powershell
python -m pip install --upgrade --force-reinstall "git+https://github.com/OWNER/MiniPy3DR.git@main"
```

## 先生側: GitHub に置く手順

```powershell
git status
git add .
git commit -m "Prepare MiniPy3DR package install"
git branch -M main
git remote add origin https://github.com/OWNER/MiniPy3DR.git
git push -u origin main
git tag v0.3.0
git push origin v0.3.0
```

すでに remote がある場合は `git remote add origin ...` は不要です。

## 動作確認

別フォルダで次を実行します。

```powershell
python -m pip install "git+https://github.com/OWNER/MiniPy3DR.git@main"
python -c "from minipy3dr import App; print(App)"
```

`<class 'minipy3dr.app.MiniPy3DRApp'>` のように表示されれば OK です。

## 注意

GitHub からインストールされるのは push 済みの内容だけです。
ローカルで編集しただけのファイルは、生徒の PC には入りません。
