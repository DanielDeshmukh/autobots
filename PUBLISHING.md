# Publishing Autobots

Current package version:

- `0.1.1`

Package metadata source:

- [setup.cfg](/d:/Vs%20Code/VS%20code/autobots/setup.cfg)

## Install locally in editable mode

```powershell
python -m pip install --upgrade pip setuptools wheel build twine
python -m pip install -e . --no-build-isolation
autobots
```

Verify metadata:

```powershell
python -m pip show autobot-swarm
```

Expected author fields:

- `Author: Daniel Deshmukh`
- `Author-email: deshmukhdaniel2005@gmail.com`

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

Optional sanity check before upload:

```powershell
python -m twine check dist/*
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
