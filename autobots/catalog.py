from __future__ import annotations

import importlib.util
import json
import os
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType


@dataclass(frozen=True)
class ModelSpec:
    model_id: str
    cluster: str
    tags: tuple[str, ...]


@dataclass(frozen=True)
class ClusterSpec:
    name: str
    role: str
    keywords: tuple[str, ...]
    models: tuple[ModelSpec, ...]


CLUSTER_DEFINITIONS = {
    "Optimus": {
        "role": "command-and-routing",
        "keywords": (
            "plan",
            "roadmap",
            "route",
            "phase",
            "architecture",
            "orchestrate",
            "requirements",
        ),
        "models": [
            "nvidia/nemotron-3-super-120b-a12b",
            "nvidia/llama-3.3-nemotron-super-49b-v1.5",
            "nvidia/mistral-large-3-675b-instruct-2512",
            "nvidia/kimi-k2-thinking",
            "nvidia/step-3.5-flash",
            "nvidia/gpt-oss-120b",
            "nvidia/glm-5.1",
            "nvidia/llama-4-maverick-17b-128e-instruct",
            "nvidia/stockmark-2-100b-instruct",
        ],
    },
    "UltraMagnus": {
        "role": "backend-and-architecture",
        "keywords": (
            "backend",
            "api",
            "architecture",
            "database",
            "service",
            "logic",
            "integration",
            "python",
        ),
        "models": [
            "nvidia/kimi-k2.6",
            "nvidia/deepseek-v4-pro",
            "nvidia/qwen3.5-397b-a17b",
            "nvidia/mistral-medium-3.5-128b",
            "nvidia/gemma-4-31b-it",
            "nvidia/qwen3-next-80b-a3b-thinking",
            "nvidia/dracarys-llama-3.1-70b-instruct",
            "nvidia/mixtral-8x22b-instruct-v0.1",
            "nvidia/evo2-40b",
            "nvidia/boltz-2",
            "nvidia/alphafold2-multimer",
            "nvidia/msa-search",
        ],
    },
    "RedAlert": {
        "role": "security-and-safety",
        "keywords": (
            "security",
            "auth",
            "safety",
            "guardrail",
            "pii",
            "policy",
            "validation",
        ),
        "models": [
            "nvidia/llama-3.1-nemotron-70b-instruct",
            "nvidia/nemotron-4-340b-instruct",
            "deepseek-ai/deepseek-v4-pro",
            "nvidia/llama-3.1-nemotron-51b-instruct",
            "meta/llama-3.1-405b-instruct",
            "deepseek-ai/deepseek-v4-flash",
            "nvidia/llama-3.3-nemotron-super-49b-v1.5",
            "nvidia/mistral-large-3-675b-instruct-2512",
            "nvidia/qwen3.5-397b-a17b",
            "nvidia/mistral-medium-3.5-128b",
        ],
    },
    "Jazz": {
        "role": "frontend-and-creative",
        "keywords": (
            "ui",
            "ux",
            "frontend",
            "css",
            "tailwind",
            "image",
            "visual",
            "component",
        ),
        "models": [
            "nvidia/qwen-image-edit",
            "nvidia/qwen-image",
            "nvidia/flux.2-klein-4b",
            "nvidia/flux.1-dev",
            "nvidia/flux.1-schnell",
            "nvidia/stable-diffusion-3.5-large",
            "nvidia/FLUX.1-Kontext-dev",
            "nvidia/phi-4-multimodal-instruct",
            "nvidia/NVIDIA AI for Media Relighting",
            "nvidia/TRELLIS",
            "nvidia/vista-3d",
        ],
    },
    "Ratchet": {
        "role": "debug-and-repair",
        "keywords": (
            "debug",
            "fix",
            "refactor",
            "patch",
            "repair",
            "test",
            "stability",
        ),
        "models": [
            "nvidia/deepseek-v4-flash",
            "nvidia/qwen3.5-coder-480b-a35b-instruct",
            "nvidia/qwen2.5-coder-32b-instruct",
            "nvidia/mistral-small-4-119b-2603",
            "nvidia/devstral-2-123b-instruct-2512",
            "nvidia/magistral-small-2506",
            "nvidia/phi-4-mini-instruct",
            "nvidia/llama-3.2-3b-instruct",
            "nvidia/llama-3.2-1b-instruct",
            "nvidia/nemotron-mini-4b-instruct",
        ],
    },
    "Perceptor": {
        "role": "retrieval-and-parsing",
        "keywords": (
            "ocr",
            "rag",
            "retrieval",
            "search",
            "embedding",
            "document",
            "parse",
        ),
        "models": [
            "nvidia/nemotron-ocr-v1",
            "nvidia/nemotron-parse",
            "nvidia/paddleocr",
            "nvidia/nemotron-table-structure-v1",
            "nvidia/nemotron-page-elements-v3",
            "nvidia/nemotron-graphic-elements-v1",
            "nvidia/llama-3.2-nemoretriever-300m-embed-v2",
            "nvidia/llama-3.2-nv-embedqa-1b-v2",
            "nvidia/llama-3.2-nv-rerankqa-1b-v2",
            "nvidia/nv-embedcode-7b-v1",
            "nvidia/bge-m3",
            "nvidia/rerank-qa-mistral-4b",
        ],
    },
    "Bumblebee": {
        "role": "communication-and-media",
        "keywords": (
            "speech",
            "voice",
            "translation",
            "transcription",
            "media",
            "video",
            "audio",
        ),
        "models": [
            "nvidia/whisper-large-v3",
            "nvidia/canary-1b-asr",
            "nvidia/riva-translate-4b-instruct-v1_1",
            "nvidia/magpie-tts-zeroshot",
            "nvidia/nemotron-voicechat",
            "nvidia/LipSync",
            "nvidia/Background Noise Removal",
            "nvidia/Active Speaker Detection",
            "nvidia/parakeet-1.1b-rnnt-multilingual-asr",
        ],
    },
    "Ironhide": {
        "role": "physical-and-simulation",
        "keywords": (
            "simulation",
            "physics",
            "autonomous",
            "optimization",
            "routing",
            "prediction",
        ),
        "models": [
            "nvidia/cosmos-reason2-8b",
            "nvidia/cosmos-transfer2.5-2b",
            "nvidia/cosmos-predict1-5b",
            "nvidia/streampetr",
            "nvidia/sparsedrive",
            "nvidia/bevformer",
            "nvidia/fourcastnet",
            "nvidia/cuopt",
        ],
    },
    "Wheeljack": {
        "role": "scientific-specialist",
        "keywords": (
            "science",
            "molecule",
            "protein",
            "quantum",
            "biology",
            "research",
        ),
        "models": [
            "nvidia/ising-calibration-1-35b-a3b",
            "nvidia/genmol",
            "nvidia/molmim",
            "nvidia/rfdiffusion",
            "nvidia/proteinmpnn",
            "nvidia/esm2-650m",
            "nvidia/openfold3",
        ],
    },
}

ENGINE_ROOT = Path(__file__).resolve().parent.parent
ENDPOINT_DISCOVERY_PATH = ENGINE_ROOT / "find_endpoints.py"
GENERAL_TEXT_MODEL_TOKENS = (
    "assistant",
    "chat",
    "coder",
    "deepseek",
    "flash",
    "gemma",
    "glm",
    "gpt",
    "instruct",
    "kimi",
    "llama",
    "magistral",
    "mistral",
    "nemotron",
    "qwen",
    "reason",
    "small",
    "step",
    "super",
    "think",
)
CLUSTER_MATCH_TOKENS = {
    "Optimus": ("command", "glm", "gpt", "kimi", "maverick", "nemotron", "reason", "step", "stockmark", "super", "think"),
    "UltraMagnus": ("alphafold", "backend", "boltz", "code", "coder", "deepseek", "gemma", "kimi", "mixtral", "mistral", "qwen"),
    "RedAlert": ("content-safety", "guard", "jailbreak", "moderation", "nemoguard", "pii", "safety", "topic-control", "usdvalidate", "validate"),
    "Jazz": ("diffusion", "edit", "flux", "image", "kontext", "multimodal", "relighting", "sd3", "trellis", "vista"),
    "Ratchet": ("coder", "debug", "devstral", "fix", "flash", "mini", "patch", "phi", "repair", "small"),
    "Perceptor": ("bge", "document", "embed", "graphic", "ocr", "page", "parse", "paddleocr", "rerank", "retriever", "table"),
    "Bumblebee": ("asr", "audio", "canary", "lipsync", "noise", "parakeet", "speaker", "speech", "translate", "tts", "voice", "whisper"),
    "Ironhide": ("autonomous", "bevformer", "cosmos", "cuopt", "fourcastnet", "physics", "predict", "simulation", "sparsedrive", "streampetr", "transfer"),
    "Wheeljack": ("alphafold", "biology", "esm", "evo", "fold", "genmol", "ising", "mol", "molecule", "msa", "protein", "rfdiffusion"),
}
DISCOVERY_MODULE: ModuleType | None = None


class ClusterCatalog:
    def __init__(
        self,
        extra_registry_path: str | None = None,
        *,
        api_key: str | None = None,
        refresh_live: bool | None = None,
        available_model_ids: list[str] | None = None,
    ):
        self.extra_registry_path = extra_registry_path or os.getenv("AUTOBOTS_MODEL_REGISTRY")
        self.api_key = (api_key or os.getenv("NVIDIA_API_KEY") or "").strip() or None
        self._manual_available_model_ids = tuple(dict.fromkeys(available_model_ids or ()))
        self.refresh_live = refresh_live if refresh_live is not None else bool(
            self.api_key and os.getenv("AUTOBOTS_DISABLE_LIVE_CATALOG", "0") != "1"
        )
        self.discovery_error: str | None = None
        self.using_live_catalog = False
        self.available_model_ids = self._resolve_available_model_ids()
        self.clusters = self._build_clusters()

    @property
    def model_count(self) -> int:
        return sum(len(cluster.models) for cluster in self.clusters.values())

    @property
    def available_model_count(self) -> int:
        return len(self.available_model_ids)

    def cluster_names(self) -> list[str]:
        return list(self.clusters.keys())

    def cluster_model_counts(self) -> list[tuple[str, str, int]]:
        return [
            (cluster.name, cluster.role, len(cluster.models))
            for cluster in self.clusters.values()
        ]

    def route(self, task_signal: str) -> str:
        normalized = task_signal.lower()
        scored: list[tuple[int, str]] = []
        for cluster in self.clusters.values():
            score = sum(1 for keyword in cluster.keywords if keyword in normalized)
            scored.append((score, cluster.name))

        scored.sort(key=lambda item: item[0], reverse=True)
        best_score, best_cluster = scored[0]
        if best_score == 0:
            return "UltraMagnus"
        return best_cluster

    def get_cluster(self, name: str) -> ClusterSpec:
        return self.clusters[name]

    def select_models(self, cluster_name: str, task_signal: str) -> tuple[ModelSpec, ModelSpec, list[ModelSpec]]:
        cluster = self.get_cluster(cluster_name)
        ranked = sorted(
            cluster.models,
            key=lambda model: self._score_model(model, task_signal),
            reverse=True,
        )
        lead = ranked[0]
        reviewer = ranked[1] if len(ranked) > 1 else ranked[0]
        support = ranked[2:5]
        return lead, reviewer, support

    def _score_model(self, model: ModelSpec, task_signal: str) -> int:
        normalized = task_signal.lower()
        return sum(1 for tag in model.tags if tag in normalized)

    def _build_clusters(self) -> dict[str, ClusterSpec]:
        live_cluster_models = self._build_live_cluster_models()
        clusters: dict[str, ClusterSpec] = {}
        for cluster_name, spec in CLUSTER_DEFINITIONS.items():
            tags = spec["keywords"]
            model_ids = live_cluster_models.get(cluster_name) or spec["models"]
            models = tuple(ModelSpec(model_id=model_id, cluster=cluster_name, tags=tags) for model_id in model_ids)
            clusters[cluster_name] = ClusterSpec(
                name=cluster_name,
                role=spec["role"],
                keywords=tags,
                models=models,
            )

        for cluster_name, model_ids in self._load_extra_registry().items():
            if cluster_name not in clusters:
                clusters[cluster_name] = ClusterSpec(
                    name=cluster_name,
                    role="custom",
                    keywords=(),
                    models=tuple(ModelSpec(model_id=model_id, cluster=cluster_name, tags=()) for model_id in model_ids),
                )
                continue

            existing = list(clusters[cluster_name].models)
            existing_ids = {model.model_id for model in existing}
            for model_id in model_ids:
                if model_id not in existing_ids:
                    existing.append(
                        ModelSpec(
                            model_id=model_id,
                            cluster=cluster_name,
                            tags=clusters[cluster_name].keywords,
                        )
                    )
            clusters[cluster_name] = ClusterSpec(
                name=clusters[cluster_name].name,
                role=clusters[cluster_name].role,
                keywords=clusters[cluster_name].keywords,
                models=tuple(existing),
            )

        return clusters

    def _load_extra_registry(self) -> dict[str, list[str]]:
        if not self.extra_registry_path:
            return {}

        path = Path(self.extra_registry_path).expanduser()
        if not path.exists():
            return {}

        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return {}

        extra: dict[str, list[str]] = {}
        for cluster_name, model_ids in payload.items():
            if isinstance(model_ids, list):
                extra[cluster_name] = [str(model_id) for model_id in model_ids]
        return extra

    def _resolve_available_model_ids(self) -> tuple[str, ...]:
        if self._manual_available_model_ids:
            self.using_live_catalog = True
            return self._manual_available_model_ids

        if not self.refresh_live or not self.api_key:
            return ()

        try:
            discovery = self._load_discovery_module()
            model_ids = discovery.fetch_available_nim_model_ids(self.api_key)
        except Exception as exc:
            self.discovery_error = str(exc)
            return ()

        self.using_live_catalog = True
        return tuple(dict.fromkeys(model_ids))

    def _build_live_cluster_models(self) -> dict[str, list[str]]:
        if not self.available_model_ids:
            return {}

        available_ids = list(self.available_model_ids)
        available_by_lower = {model_id.lower(): model_id for model_id in available_ids}
        available_by_name = {self._canonical_model_name(model_id): model_id for model_id in available_ids}
        cluster_models = {cluster_name: [] for cluster_name in CLUSTER_DEFINITIONS}

        for cluster_name, spec in CLUSTER_DEFINITIONS.items():
            for seed_model_id in spec["models"]:
                matched = available_by_lower.get(seed_model_id.lower())
                if matched is None:
                    matched = available_by_name.get(self._canonical_model_name(seed_model_id))
                if matched and matched not in cluster_models[cluster_name]:
                    cluster_models[cluster_name].append(matched)

        for model_id in available_ids:
            for cluster_name in self._matching_clusters(model_id):
                if model_id not in cluster_models[cluster_name]:
                    cluster_models[cluster_name].append(model_id)

        general_pool = [model_id for model_id in available_ids if self._looks_like_general_text_model(model_id)]
        fallback_pool = general_pool or available_ids
        for cluster_name in CLUSTER_DEFINITIONS:
            if cluster_models[cluster_name]:
                continue
            cluster_models[cluster_name] = fallback_pool[: min(3, len(fallback_pool))]

        return cluster_models

    def _matching_clusters(self, model_id: str) -> list[str]:
        normalized = model_id.lower()
        matches: list[str] = []
        for cluster_name, tokens in CLUSTER_MATCH_TOKENS.items():
            if any(token in normalized for token in tokens):
                matches.append(cluster_name)

        if not matches and self._looks_like_general_text_model(model_id):
            matches.extend(["Optimus", "UltraMagnus", "Ratchet"])

        if not matches:
            matches.append("Optimus")
        return matches

    def _looks_like_general_text_model(self, model_id: str) -> bool:
        normalized = model_id.lower()
        return any(token in normalized for token in GENERAL_TEXT_MODEL_TOKENS)

    def _canonical_model_name(self, model_id: str) -> str:
        return model_id.lower().split("/", 1)[-1]

    def _load_discovery_module(self):
        global DISCOVERY_MODULE

        if DISCOVERY_MODULE is not None:
            return DISCOVERY_MODULE

        spec = importlib.util.spec_from_file_location("autobots_find_endpoints", ENDPOINT_DISCOVERY_PATH)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Unable to load endpoint discovery script at {ENDPOINT_DISCOVERY_PATH}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        DISCOVERY_MODULE = module
        return module
