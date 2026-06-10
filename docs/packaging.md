# MiniPy3DR packaging notes

This project uses `pyproject.toml` with setuptools.

## Student install from PyPI

For classroom Windows PCs, use the prebuilt wheel published to PyPI. This avoids
requiring Visual Studio Build Tools on student machines.

```powershell
python -m pip install minipy3dr
```

To pin a class to one release:

```powershell
python -m pip install "minipy3dr==0.4.1"
```

pip selects the matching `cp310`, `cp311`, `cp312`, or `cp313` `win_amd64`
wheel and installs it without compiling C++ on the student PC.

## Install from GitHub source

After pushing the repository to GitHub, users can install it directly:

```powershell
python -m pip install "git+https://github.com/andogensi/MiniPy3DR.git"
```

This builds from source on the local PC, so it is mainly for teacher machines
and development. It is not the classroom default.

With uv:

```powershell
uv pip install "git+https://github.com/andogensi/MiniPy3DR.git"
```

Install a branch:

```powershell
python -m pip install "git+https://github.com/andogensi/MiniPy3DR.git@main"
```

With uv:

```powershell
uv pip install "git+https://github.com/andogensi/MiniPy3DR.git@main"
```

Install a version tag:

```powershell
python -m pip install "git+https://github.com/andogensi/MiniPy3DR.git@v0.4.1"
```

Force reinstall after pushing changes:

```powershell
python -m pip install --upgrade --force-reinstall "git+https://github.com/andogensi/MiniPy3DR.git@main"
```

For private repositories, students need GitHub access and a working Git credential setup.

## PyPI release checklist

The GitHub Actions workflow uses PyPI trusted publishing. In PyPI, add a trusted
publisher or pending publisher with these values:

- PyPI project name: `minipy3dr`
- Owner: `andogensi`
- Repository: `MiniPy3DR`
- Workflow: `wheels.yml`
- Environment: `pypi`

Then publish by pushing a version tag:

```powershell
git status
# Update pyproject.toml and minipy3dr/__init__.py to the new version first.
git add .
git commit -m "Prepare MiniPy3DR release"
git branch -M main
git remote add origin https://github.com/andogensi/MiniPy3DR.git
git push -u origin main
git tag v0.4.1
git push origin v0.4.1
```

Tag pushes run the `Build and publish package` GitHub Actions workflow. Windows
wheels for Python 3.10 through 3.13 and the source distribution are uploaded to
PyPI. The Windows wheels include the native C++ renderer.

The wheel workflow sets `MINIPY3DR_REQUIRE_NATIVE=1`, so a release wheel fails
to build if the native extension is missing. Normal source installs keep the
extension optional and fall back to the Python/NumPy renderer when no compiler is
available.

## Local install

```powershell
python -m pip install .
```

## Editable install for lessons

Use this while editing the library or examples:

```powershell
python -m pip install -e .
```

With uv:

```powershell
uv pip install -e .
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

With uv:

```powershell
uv pip install -e ".[dev]"
uv run python -m build
```

For a local smoke wheel with the current environment:

```powershell
python -m pip wheel . --no-deps --no-build-isolation --wheel-dir dist
```

For a release-grade local wheel, install a C++ compiler and require the native
extension explicitly:

```powershell
$env:MINIPY3DR_REQUIRE_NATIVE = "1"
python -m pip wheel . --no-deps --no-build-isolation --wheel-dir dist
```

## Check package metadata

```powershell
python -m twine check dist/*
```

## What goes into the wheel

Only the `minipy3dr` package is included in the installable wheel.
Docs, examples, and tests stay in the repository for teaching and development.
