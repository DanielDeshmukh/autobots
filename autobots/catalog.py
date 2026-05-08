from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


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
            "nemotron-3-super-120b-a12b",
            "llama-3.3-nemotron-super-49b-v1.5",
            "mistral-large-3-675b-instruct-2512",
            "kimi-k2-thinking",
            "step-3.5-flash",
            "gpt-oss-120b",
            "glm-5.1",
            "llama-4-maverick-17b-128e-instruct",
            "stockmark-2-100b-instruct",
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
            "kimi-k2.6",
            "deepseek-v4-pro",
            "qwen3.5-397b-a17b",
            "mistral-medium-3.5-128b",
            "gemma-4-31b-it",
            "qwen3-next-80b-a3b-thinking",
            "dracarys-llama-3.1-70b-instruct",
            "mixtral-8x22b-instruct-v0.1",
            "evo2-40b",
            "boltz-2",
            "alphafold2-multimer",
            "msa-search",
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
            "nemotron-3-content-safety",
            "llama-3.1-nemotron-safety-guard-8b-v3",
            "gliner-pii",
            "llama-guard-4-12b",
            "nemoguard-jailbreak-detect",
            "llama-3.1-nemoguard-8b-topic-control",
            "llama-3.1-nemoguard-8b-content-safety",
            "nemotron-content-safety-reasoning-4b",
            "synthetic-video-detector",
            "usdvalidate",
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
            "qwen-image-edit",
            "qwen-image",
            "flux.2-klein-4b",
            "flux.1-dev",
            "flux.1-schnell",
            "stable-diffusion-3.5-large",
            "FLUX.1-Kontext-dev",
            "phi-4-multimodal-instruct",
            "NVIDIA AI for Media Relighting",
            "TRELLIS",
            "vista-3d",
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
            "deepseek-v4-flash",
            "qwen3.5-coder-480b-a35b-instruct",
            "qwen2.5-coder-32b-instruct",
            "mistral-small-4-119b-2603",
            "devstral-2-123b-instruct-2512",
            "magistral-small-2506",
            "phi-4-mini-instruct",
            "llama-3.2-3b-instruct",
            "llama-3.2-1b-instruct",
            "nemotron-mini-4b-instruct",
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
            "nemotron-ocr-v1",
            "nemotron-parse",
            "paddleocr",
            "nemotron-table-structure-v1",
            "nemotron-page-elements-v3",
            "nemotron-graphic-elements-v1",
            "llama-3.2-nemoretriever-300m-embed-v2",
            "llama-3.2-nv-embedqa-1b-v2",
            "llama-3.2-nv-rerankqa-1b-v2",
            "nv-embedcode-7b-v1",
            "bge-m3",
            "rerank-qa-mistral-4b",
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
            "whisper-large-v3",
            "canary-1b-asr",
            "riva-translate-4b-instruct-v1_1",
            "magpie-tts-zeroshot",
            "nemotron-voicechat",
            "LipSync",
            "Background Noise Removal",
            "Active Speaker Detection",
            "parakeet-1.1b-rnnt-multilingual-asr",
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
            "cosmos-reason2-8b",
            "cosmos-transfer2.5-2b",
            "cosmos-predict1-5b",
            "streampetr",
            "sparsedrive",
            "bevformer",
            "fourcastnet",
            "cuopt",
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
            "ising-calibration-1-35b-a3b",
            "genmol",
            "molmim",
            "rfdiffusion",
            "proteinmpnn",
            "esm2-650m",
            "openfold3",
        ],
    },
}


class ClusterCatalog:
    def __init__(self, extra_registry_path: str | None = None):
        self.extra_registry_path = extra_registry_path or os.getenv("AUTOBOTS_MODEL_REGISTRY")
        self.clusters = self._build_clusters()

    @property
    def model_count(self) -> int:
        return sum(len(cluster.models) for cluster in self.clusters.values())

    def cluster_names(self) -> list[str]:
        return list(self.clusters.keys())

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
        clusters: dict[str, ClusterSpec] = {}
        for cluster_name, spec in CLUSTER_DEFINITIONS.items():
            tags = spec["keywords"]
            models = tuple(ModelSpec(model_id=model_id, cluster=cluster_name, tags=tags) for model_id in spec["models"])
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

