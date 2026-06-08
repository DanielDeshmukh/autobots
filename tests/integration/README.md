# Integration Tests

These tests hit the **live NVIDIA NIM API** and require a valid `NVIDIA_API_KEY`.

## Running

```bash
# With API key (Windows PowerShell)
$env:NVIDIA_API_KEY="nvapi-xxx"; python -m pytest tests/integration/ -v

# With API key (Linux/macOS)
NVIDIA_API_KEY=nvapi-xxx pytest tests/integration/ -v

# Without API key — tests auto-skip
pytest tests/integration/ -v
```

## What's tested

| File | Tests | Description |
|------|-------|-------------|
| `test_api_connectivity.py` | 5 | Model reachability, JSON contract, skill injection |
| `test_full_pipeline.py` | 5 | Full router pipeline, specialist/review JSON contracts |

## Adding tests

Place new integration tests in this directory. They will automatically skip when `NVIDIA_API_KEY` is not set via the `conftest.py` hook.
