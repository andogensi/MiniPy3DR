# MiniPy3DR packaging notes

This project uses `pyproject.toml` with setuptools.

## Install from GitHub

After pushing the repository to GitHub, users can install it directly:

```powershell
python -m pip install "git+https://github.com/andogensi/MiniPy3DR.git"
```

Install a branch:

```powershell
python -m pip install "git+https://github.com/andogensi/MiniPy3DR.git@main"
```

Install a version tag:

```powershell
python -m pip install "git+https://github.com/andogensi/MiniPy3DR.git@v0.3.0"
```

Force reinstall after pushing changes:

```powershell
python -m pip install --upgrade --force-reinstall "git+https://github.com/andogensi/MiniPy3DR.git@main"
```

For private repositories, students need GitHub access and a working Git credential setup.

## GitHub release checklist

```powershell
git status
git add .
git commit -m "Prepare MiniPy3DR package install"
git branch -M main
git remote add origin https://github.com/andogensi/MiniPy3DR.git
git push -u origin main
git tag v0.3.0
git push origin v0.3.0
```

## Local install

```powershell
python -m pip install .
```

## Editable install for lessons

Use this while editing the library or examples:

```powershell
python -m pip install -e .
```

If Pygame and NumPy are already installed and the classroom has no network, use:

```powershell
python -m pip install -e . --no-deps
```

## Build wheel and sdist

```powershell
python -m pip install -e ".[dev]"
python -m build
```

For a quick wheel build without installing extra build tools:

```powershell
python -m pip wheel . --no-deps --no-build-isolation --wheel-dir dist
```

## Check package metadata

```powershell
python -m twine check dist/*
```

## What goes into the wheel

Only the `minipy3dr` package is included in the installable wheel.
Docs, examples, and tests stay in the repository for teaching and development.
