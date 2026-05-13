# Publishing Autobots

## Install locally in editable mode

```powershell
python -m pip install --upgrade pip setuptools wheel build twine
python -m pip install -e . --no-build-isolation
autobots
```

## Build distributable packages

```powershell
python -m build --no-isolation
```

This creates:

- `dist/*.whl`
- `dist/*.tar.gz`

## Publish to TestPyPI first

```powershell
python -m twine upload --repository testpypi dist/*
```

Install from TestPyPI:

```powershell
python -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple autobot-swarm
```

## Publish to PyPI

```powershell
python -m twine upload dist/*
```

## Result

Users install with:

```powershell
pip install autobot-swarm
```

Users run with:

```powershell
autobots
```

## Metadata

- Author: `Daniel Deshmukh`
- Email: `deshmukhdaniel2005@gmail.com`
- Homepage: `https://github.com/DanielDeshmukh`
- Repository: `https://github.com/DanielDeshmukh/autobots`
