"""update_models.py — Fetch latest NVIDIA NIM models and save categorized catalog.

Usage:
    python update_models.py              # Update JSON catalog
    python update_models.py --markdown   # Also generate markdown report
"""

import json, os, sys, time
from datetime import datetime
from pathlib import Path
from openai import OpenAI

API_URL = "https://integrate.api.nvidia.com/v1/models"
OUTPUT_DIR = Path(__file__).parent.parent
CATALOG_JSON = OUTPUT_DIR / "nvidia_models.json"
CATALOG_MD = OUTPUT_DIR / "NVIDIA_MODELS.md"

# Known model categories (manually maintained, updated as we discover new models)
MODEL_CATEGORIES = {
    "text-generation": [
        "nvidia/nemotron-3-ultra-550b-a55b",
        "nvidia/nemotron-3-super-120b-a12b",
        "nvidia/nemotron-4-340b-instruct",
        "nvidia/llama-3.1-nemotron-70b-instruct",
        "nvidia/llama-3.1-nemotron-51b-instruct",
        "nvidia/llama-3.1-nemotron-ultra-253b-v1",
        "nvidia/llama-3.3-nemotron-super-49b-v1",
        "nvidia/llama-3.3-nemotron-super-49b-v1.5",
        "nvidia/nvidia-nemotron-nano-9b-v2",
        "nvidia/llama-3.1-nemotron-nano-8b-v1",
        "nvidia/nemotron-3-nano-30b-a3b",
        "nvidia/nemotron-mini-4b-instruct",
        "meta/llama-3.3-70b-instruct",
        "meta/llama-3.1-70b-instruct",
        "meta/llama-3.1-8b-instruct",
        "meta/llama-3.2-3b-instruct",
        "meta/llama-3.2-1b-instruct",
        "meta/llama-4-maverick-17b-128e-instruct",
        "qwen/qwen3.5-397b-a17b",
        "qwen/qwen3.5-122b-a10b",
        "qwen/qwen3-next-80b-a3b-instruct",
        "deepseek-ai/deepseek-v4-flash",
        "deepseek-ai/deepseek-v4-pro",
        "mistralai/mistral-large-3-675b-instruct-2512",
        "mistralai/mistral-medium-3.5-128b",
        "mistralai/mistral-small-4-119b-2603",
        "mistralai/mistral-nemotron",
        "mistralai/mixtral-8x7b-instruct-v0.1",
        "moonshotai/kimi-k2.6",
        "stepfun-ai/step-3.7-flash",
        "stepfun-ai/step-3.5-flash",
        "z-ai/glm-5.1",
        "minimaxai/minimax-m3",
        "minimaxai/minimax-m2.7",
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "microsoft/phi-4-mini-instruct",
        "google/gemma-4-31b-it",
        "google/gemma-3-12b-it",
        "google/gemma-3-4b-it",
        "google/gemma-3n-e2b-it",
        "google/gemma-3n-e4b-it",
        "google/gemma-2-2b-it",
        "ibm/granite-3.0-8b-instruct",
        "ibm/granite-34b-code-instruct",
        "bytedance/seed-oss-36b-instruct",
        "writer/palmyra-creative-122b",
        "writer/palmyra-fin-70b-32k",
        "writer/palmyra-med-70b",
        "stockmark/stockmark-2-100b-instruct",
        "sarvamai/sarvam-m",
        "upstage/solar-10.7b-instruct",
        "zyphra/zamba2-7b-instruct",
    ],
    "vision": [
        "nvidia/llama-3.1-nemotron-nano-vl-8b-v1",
        "nvidia/nemotron-nano-12b-v2-vl",
        "nvidia/neva-22b",
        "nvidia/vila",
        "meta/llama-3.2-11b-vision-instruct",
        "meta/llama-3.2-90b-vision-instruct",
        "microsoft/phi-4-multimodal-instruct",
        "microsoft/phi-3-vision-128k-instruct",
        "microsoft/kosmos-2",
        "google/paligemma",
    ],
    "image-generation": [
        "black-forest-labs/flux.1-schnell",
        "black-forest-labs/flux.1-dev",
        "stabilityai/stable-diffusion-3.5-large",
        "qwen/qwen-image",
        "qwen/qwen-image-edit",
    ],
    "video": [
        "nvidia/cosmos-reason2-8b",
        "nvidia/ai-synthetic-video-detector",
    ],
    "speech": [
        "nvidia/nemotron-asr-streaming",
        "nvidia/parakeet-tdt-0.6b-v2",
        "nvidia/canary-1b-asr",
        "openai/whisper-large-v3",
        "nvidia/magpie-tts-zeroshot",
        "nvidia/magpie-tts-multilingual",
        "nvidia/studiovoice",
    ],
    "embedding": [
        "nvidia/llama-nemotron-embed-1b-v2",
        "nvidia/llama-nemotron-embed-vl-1b-v2",
        "nvidia/nv-embedqa-e5-v5",
        "nvidia/nv-embed-v1",
        "nvidia/nv-embedcode-7b-v1",
        "nvidia/embed-qa-4",
        "nvidia/llama-3.2-nv-embedqa-1b-v1",
        "baai/bge-m3",
        "snowflake/arctic-embed-l",
    ],
    "safety": [
        "nvidia/nemotron-3-content-safety",
        "nvidia/nemotron-3.5-content-safety",
        "nvidia/nemotron-content-safety-reasoning-4b",
        "nvidia/llama-3.1-nemotron-safety-guard-8b-v3",
        "nvidia/llama-3.1-nemoguard-8b-content-safety",
        "nvidia/llama-3.1-nemoguard-8b-topic-control",
        "meta/llama-guard-4-12b",
    ],
    "ocr": [
        "nvidia/nemotron-parse",
        "nvidia/nemoretriever-parse",
    ],
    "specialized": [
        "nvidia/ising-calibration-1-35b-a3b",
        "nvidia/riva-translate-4b-instruct",
        "nvidia/gliner-pii",
    ],
}


def fetch_models():
    """Fetch all models from NVIDIA NIM API."""
    client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key="no-key")
    # The /v1/models endpoint doesn't require auth
    import urllib.request
    req = urllib.request.Request(API_URL)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    return data.get("data", [])


def categorize_model(model_id):
    """Return category for a model ID."""
    for category, ids in MODEL_CATEGORIES.items():
        if model_id in ids:
            return category
    return "other"


def build_catalog(models):
    """Build categorized catalog from raw model list."""
    catalog = {
        "fetched_at": datetime.now().isoformat(),
        "total": len(models),
        "by_category": {},
        "by_publisher": {},
        "models": {},
    }

    for m in models:
        mid = m["id"]
        publisher = m.get("owned_by", "unknown")
        category = categorize_model(mid)

        # Add to category
        catalog["by_category"].setdefault(category, []).append(mid)

        # Add to publisher
        catalog["by_publisher"].setdefault(publisher, []).append(mid)

        # Store model info
        catalog["models"][mid] = {
            "id": mid,
            "publisher": publisher,
            "category": category,
            "created": m.get("created"),
        }

    # Sort lists
    for cat in catalog["by_category"]:
        catalog["by_category"][cat].sort()
    for pub in catalog["by_publisher"]:
        catalog["by_publisher"][pub].sort()

    return catalog


def generate_markdown(catalog):
    """Generate markdown report from catalog."""
    lines = [
        "# NVIDIA NIM Models — Auto-Updated Catalog",
        f"\nFetched: {catalog['fetched_at']} | Total: {catalog['total']} models\n",
        "---\n",
    ]

    # By category
    lines.append("## By Category\n")
    for cat in sorted(catalog["by_category"].keys()):
        models = catalog["by_category"][cat]
        lines.append(f"### {cat.replace('-', ' ').title()} ({len(models)})\n")
        for mid in models:
            m = catalog["models"][mid]
            lines.append(f"- `{mid}` ({m['publisher']})")
        lines.append("")

    # By publisher
    lines.append("## By Publisher\n")
    for pub in sorted(catalog["by_publisher"].keys()):
        models = catalog["by_publisher"][pub]
        lines.append(f"### {pub} ({len(models)})\n")
        for mid in models:
            m = catalog["models"][mid]
            lines.append(f"- `{mid}` [{m['category']}]")
        lines.append("")

    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--markdown", action="store_true", help="Also generate markdown")
    args = parser.parse_args()

    print("Fetching models from NVIDIA NIM API...")
    models = fetch_models()
    print(f"  Found {len(models)} models")

    print("Building catalog...")
    catalog = build_catalog(models)

    print(f"  Categories: {list(catalog['by_category'].keys())}")
    print(f"  Publishers: {len(catalog['by_publisher'])}")

    # Save JSON
    CATALOG_JSON.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    print(f"  Saved: {CATALOG_JSON}")

    # Save markdown if requested
    if args.markdown:
        md = generate_markdown(catalog)
        CATALOG_MD.write_text(md, encoding="utf-8")
        print(f"  Saved: {CATALOG_MD}")

    # Summary
    print(f"\nSummary:")
    for cat, models in sorted(catalog["by_category"].items()):
        print(f"  {cat}: {len(models)} models")


if __name__ == "__main__":
    main()
