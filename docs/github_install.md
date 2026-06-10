# PyPI と GitHub からインストールする方法

MiniPy3DR は C++ の native renderer を持っています。
生徒 PC に Visual Studio Build Tools が入っていない想定なら、
GitHub のソースを直接 `pip install` するのではなく、PyPI の
prebuilt wheel を標準にします。

## 生徒側: PyPI から入れる

```powershell
python -m pip install minipy3dr
```

pip が今使っている 64-bit Python に合う Windows wheel を PyPI から
選びます。native renderer も入るので、C++ コンパイラは不要です。

授業でバージョンを固定する場合:

```powershell
python -m pip install "minipy3dr==0.4.0"
```

native renderer の確認:

```powershell
python -c "from minipy3dr.render import is_native_available; print(is_native_available())"
```

## 先生側: GitHub のソースから入れる

MiniPy3DR は `pyproject.toml` を持っているので、GitHub に push すれば
ソースから直接 `pip install` できます。ただし、この方法は C++ 拡張を
ローカル PC でビルドしようとします。

```powershell
python -m pip install "git+https://github.com/andogensi/MiniPy3DR.git"
```

特定のブランチを入れる場合:

```powershell
python -m pip install "git+https://github.com/andogensi/MiniPy3DR.git@main"
```

タグで固定する場合:

```powershell
python -m pip install "git+https://github.com/andogensi/MiniPy3DR.git@v0.4.0"
```

更新したものを入れ直す場合:

```powershell
python -m pip install --upgrade --force-reinstall "git+https://github.com/andogensi/MiniPy3DR.git@main"
```

## 先生側: PyPI に公開する手順

初回公開前に、PyPI で trusted publisher または pending publisher を設定します。

- PyPI project name: `minipy3dr`
- Owner: `andogensi`
- Repository: `MiniPy3DR`
- Workflow: `wheels.yml`
- Environment: `pypi`

公開する前に `pyproject.toml` と `minipy3dr/__init__.py` のバージョンを合わせます。
タグを push すると GitHub Actions が Windows wheel と source distribution を
PyPI にアップロードします。

```powershell
git status
git add .
git commit -m "Prepare MiniPy3DR release"
git branch -M main
git remote add origin https://github.com/andogensi/MiniPy3DR.git
git push -u origin main
git tag v0.4.0
git push origin v0.4.0
```

すでに remote がある場合は `git remote add origin ...` は不要です。

## 動作確認

別フォルダで次を実行します。

```powershell
python -m pip install minipy3dr
python -c "from minipy3dr import App; print(App)"
```

`<class 'minipy3dr.app.MiniPy3DRApp'>` のように表示されれば OK です。

## 注意

PyPI からインストールされるのは公開済みのバージョンだけです。
ローカルで編集しただけのファイルは、生徒の PC には入りません。
