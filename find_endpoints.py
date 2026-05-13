from __future__ import annotations

import json
import os
from typing import Any
from urllib import error, request

from dotenv import load_dotenv


load_dotenv()

NIM_MODELS_URL = "https://integrate.api.nvidia.com/v1/models"


class EndpointDiscoveryError(RuntimeError):
    pass


def fetch_available_nim_models(
    api_key: str | None = None,
    *,
    timeout_seconds: int = 20,
) -> list[dict[str, Any]]:
    resolved_api_key = (api_key or os.getenv("NVIDIA_API_KEY") or "").strip()
    if not resolved_api_key:
        raise EndpointDiscoveryError("NVIDIA_API_KEY is required to discover NVIDIA NIM endpoints.")

    req = request.Request(
        NIM_MODELS_URL,
        headers={
            "Authorization": f"Bearer {resolved_api_key}",
            "Accept": "application/json",
        },
        method="GET",
    )

    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")
        raise EndpointDiscoveryError(
            f"NVIDIA model discovery failed with HTTP {exc.code}: {message}"
        ) from exc
    except error.URLError as exc:
        raise EndpointDiscoveryError(f"NVIDIA model discovery failed: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise EndpointDiscoveryError("NVIDIA model discovery returned invalid JSON.") from exc

    models = payload.get("data", [])
    if not isinstance(models, list):
        raise EndpointDiscoveryError("NVIDIA model discovery response did not contain a 'data' list.")
    return [model for model in models if isinstance(model, dict) and isinstance(model.get("id"), str)]


def fetch_available_nim_model_ids(
    api_key: str | None = None,
    *,
    timeout_seconds: int = 20,
) -> list[str]:
    seen: set[str] = set()
    model_ids: list[str] = []
    for model in fetch_available_nim_models(api_key, timeout_seconds=timeout_seconds):
        model_id = str(model["id"]).strip()
        if model_id and model_id not in seen:
            seen.add(model_id)
            model_ids.append(model_id)
    return model_ids


def main() -> None:
    try:
        model_ids = fetch_available_nim_model_ids()
    except EndpointDiscoveryError as exc:
        print(str(exc))
        raise SystemExit(1) from exc

    print(f"Found {len(model_ids)} available NVIDIA NIM models:")
    for model_id in model_ids:
        print(f"-> ID: {model_id}")


if __name__ == "__main__":
    main()
