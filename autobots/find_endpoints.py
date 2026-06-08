"""Live NVIDIA NIM catalog discovery.

Queries the NVIDIA NIM API to discover available models and returns
them as a list of model IDs for use by ClusterCatalog.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path


CACHE_DIR = Path.home() / ".autobots"
CACHE_FILE = CACHE_DIR / "catalog_cache.json"
CACHE_TTL_SECONDS = 86400  # 24 hours


def discover_models(api_key: str, *, force_refresh: bool = False) -> list[str]:
    """Discover available models from NVIDIA NIM API.
    
    Args:
        api_key: NVIDIA API key for authentication.
        force_refresh: If True, bypass cache and fetch fresh data.
        
    Returns:
        List of model ID strings available on the endpoint.
    """
    if not api_key:
        return []

    cached = _load_cache(force=force_refresh)
    if cached is not None:
        return list(cached.keys())

    models = _fetch_from_nvidia(api_key)
    if models:
        _save_cache(models)
        return list(models.keys())

    return []


def get_model_details(api_key: str) -> dict[str, dict]:
    """Get detailed model information from NVIDIA NIM.
    
    Args:
        api_key: NVIDIA API key for authentication.
        
    Returns:
        Dictionary mapping model IDs to their metadata.
    """
    if not api_key:
        return {}

    cached = _load_cache(force=False)
    if cached is not None:
        return cached

    models = _fetch_from_nvidia(api_key)
    if models:
        _save_cache(models)
        return models

    return {}


def _load_cache(*, force: bool = False) -> dict[str, dict] | None:
    """Load model cache from disk.
    
    Returns:
        Cached model data or None if cache is missing/stale.
    """
    if force:
        return None

    if not CACHE_FILE.exists():
        return None

    try:
        age = time.time() - CACHE_FILE.stat().st_mtime
        if age > CACHE_TTL_SECONDS:
            return None

        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, OSError):
        pass

    return None


def _save_cache(models: dict[str, dict]) -> None:
    """Save model data to cache.
    
    Args:
        models: Dictionary mapping model IDs to metadata.
    """
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps(models, indent=2), encoding="utf-8")
    except OSError:
        pass


def _fetch_from_nvidia(api_key: str) -> dict[str, dict]:
    """Fetch available models from NVIDIA NIM API.
    
    Args:
        api_key: NVIDIA API key.
        
    Returns:
        Dictionary mapping model IDs to metadata, or empty dict on failure.
    """
    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=api_key,
            base_url="https://integrate.api.nvidia.com/v1",
        )
        response = client.models.list()
        
        models: dict[str, dict] = {}
        for model in response.data:
            model_id = model.id
            models[model_id] = {
                "id": model_id,
                "owned_by": getattr(model, "owned_by", ""),
                "created": getattr(model, "created", 0),
            }
        
        return models
    except Exception:
        return {}
