# Autobots × NVIDIA Skills — From 100 to 1000

> **The short answer:** Yes. But not all of them. Out of ~110 NVIDIA skills listed,
> **17 are directly useful** to Autobots clusters right now, **12 are conditionally useful**
> depending on what your target project does, and the rest are irrelevant noise.
> Using the wrong ones will bloat system prompts and *hurt* performance.
> This guide tells you exactly which ones to inject, into which cluster, and why.

---

## How NVIDIA Skills Work in This Context

These aren't magic plugins. Each skill is a **structured knowledge doc** — a system-prompt-injectable blob of domain expertise. When you inject `rag-blueprint` into Optimus before it plans a RAG task, the model stops guessing about NVIDIA's RAG architecture and starts working from documented reality.

The mechanism is already in your codebase:

```python
# skills/loader.py — you already have this
skill_pack = load_skill_pack(workspace_root, cluster_name)
```

You just need to extend it to pull from an `nvidia_skills/` directory inside the project, the same way you pull from `context/`. The model doesn't care where the markdown came from.

---

## The 17 Directly Useful Skills

These work for **any** Autobots project. Inject them unconditionally.

---

### 🔴 TIER 1 — Core Cluster Upgrades (Inject These First)

These are the ones that turn a 100 into a 1000. They directly extend what your clusters already do.

---

#### 1. `nemoclaw-user-agent-skills`
**What it is:** Documents the agent skills shipped with NemoClaw — how AI coding agents are structured, what the `.agents/skills/` directory contains, integration patterns.

**Which cluster:** `Optimus` (orchestrator), `UltraMagnus` (backend)

**Why it matters:** Optimus is already your orchestrator. This skill teaches it *how NVIDIA itself structures agent skill systems*. Optimus will produce better skill pack designs, better cluster dispatch logic, and better `autobots init` scaffolding when it has this context.

**Inject as:** `context/nvidia/agent-skills.md`

---

#### 2. `nemo-rl-auto-research`
**What it is:** Autonomous research agent workflow — hypothesis testing, experiment lifecycle, directing agents through full cycles of understand → wire → launch → evaluate.

**Which cluster:** `Optimus`, `Wheeljack` (refactoring/planning)

**Why it matters:** This is literally the academic playbook for what Autobots is doing. Optimus reading this before planning a phase will produce more structured, testable, verifiable task breakdowns instead of vague instructions.

**Inject as:** `context/nvidia/autonomous-agent-research.md`

---

#### 3. `nemo-rl-session-memory`
**What it is:** Durable working-session memory for coding agents — how to preserve and recover agent context across disconnects, long-running work, handoffs.

**Which cluster:** `Optimus`, `Jazz` (test engineer)

**Why it matters:** Your checkpoint/resume system (`autobots resume`) is doing exactly this. Inject this into Optimus and it will write better checkpoint instructions and better cross-phase context handoff logic.

**Inject as:** `context/nvidia/session-memory.md`

---

#### 4. `cuopt-skill-evolution`
**What it is:** After solving a non-trivial problem, detect generalizable learnings and propose skill updates. "Always active — applies to every interaction."

**Which cluster:** `Optimus`, all clusters as a **universal suffix**

**Why it matters:** This is the self-improvement loop. After each task, the cluster reflects on what it learned and proposes updates to your `context/conventions.md`. If Autobots is building toward real autonomy, this is the mechanism that makes the swarm get smarter per project.

**Inject as:** Universal suffix on every cluster system prompt.

---

#### 5. `nemotron-policy-generator`
**What it is:** Generates custom safety policies for Nemotron content-safety guardrails — produces Markdown policy, JSON taxonomy, and drop-in inference prompts.

**Which cluster:** `Ironhide` (security reviewer)

**Why it matters:** Ironhide currently does security review based on a generic system prompt. This skill gives it a structured taxonomy for content/code safety evaluation — severity levels, policy structure, audit trail format. Ironhide's reviews become consistent and structured instead of freeform.

**Inject as:** `context/nvidia/safety-policy.md`

---

#### 6. `rag-blueprint`
**What it is:** Full NVIDIA RAG Blueprint — deploy, configure, troubleshoot, and manage. Covers Agentic RAG, every toggle, every service.

**Which cluster:** `UltraMagnus` (backend), `Optimus`

**Why it matters:** If you ever point Autobots at a RAG project (Ella, Hector, or any future RAG work), UltraMagnus with this skill knows the exact NVIDIA-recommended architecture. It stops hallucinating service names and starts writing code that matches the actual blueprint.

**Inject as:** `context/nvidia/rag-blueprint.md`

---

#### 7. `rag-eval`
**What it is:** Filesystem RAG benchmarks — corpus layout, train.json, RAGAS quality evaluation scripts.

**Which cluster:** `Jazz` (test engineer)

**Why it matters:** Jazz writing tests for a RAG system without this skill will write generic unit tests. Jazz with this skill writes RAGAS-aligned quality evaluations with proper corpus structure. This is the difference between "tests pass" and "tests prove the RAG actually works."

**Inject as:** `context/nvidia/rag-eval.md`

---

#### 8. `dynamo-recipe-runner`
**What it is:** Select, validate, patch, and deploy NVIDIA Dynamo Kubernetes recipes — model/backend/GPU/deployment-mode bring-up.

**Which cluster:** `UltraMagnus`, `Wheeljack`

**Why it matters:** If the target project involves model serving/deployment, UltraMagnus with this skill writes deployment configs that actually work on NVIDIA infrastructure instead of generic Kubernetes YAML.

**Inject as:** `context/nvidia/dynamo-deployment.md`

---

#### 9. `dynamo-router-starter`
**What it is:** Start or patch Dynamo router modes — round-robin, KV-aware, least-loaded, device-aware routing setup.

**Which cluster:** `UltraMagnus`, `Optimus`

**Why it matters:** Your own cluster routing (`autobots/router/`) is doing a simplified version of this. Inject this into Optimus and it will improve the routing logic for complex multi-model dispatch — exactly what Autobots does.

**Inject as:** `context/nvidia/dynamo-router.md`

---

#### 10. `nemo-retriever`
**What it is:** Search, query, extract, transcribe, describe across PDFs, images, DOCX, audio — any document type.

**Which cluster:** `UltraMagnus`, dedicated `Grimlock` (retrieval cluster if you add one)

**Why it matters:** Any project that needs to ingest documents (legal, medical, financial) benefits from this. UltraMagnus knows exactly how NVIDIA's retrieval pipeline handles different media types, formats, and edge cases.

**Inject as:** `context/nvidia/retrieval.md`

---

### 🟡 TIER 2 — High-Value for Specific Tasks

These are crucial when relevant, irrelevant when not. Load them **conditionally** based on what `autobots plan` detects in the roadmap.

---

#### 11. `nemotron-customize`
**Skills:** Curation, SFT/PEFT, DPO/RLVR/GRPO/RLHF, pretraining, checkpointing.

**Cluster:** `UltraMagnus`, dedicated `Soundwave` (fine-tuning cluster)

**Load when:** Target project involves model fine-tuning, training pipelines, or alignment work.

**Effect:** UltraMagnus stops writing generic HuggingFace training loops and writes Nemotron-native fine-tuning pipelines with proper curation → SFT → alignment → benchmark chains.

---

#### 12. `cuopt-numerical-optimization-api-python` + `cuopt-routing-api-python`
**Skills:** LP, MILP, QP, vehicle routing (VRP, TSP, PDP) with cuOpt Python API.

**Cluster:** `UltraMagnus`, or a dedicated `Perceptor` (optimization cluster)

**Load when:** Target project involves scheduling, logistics, route optimization, portfolio optimization, or any NP-hard combinatorial problem.

**Effect:** Instead of writing slow Python-based solvers or calling generic OR-Tools, UltraMagnus writes cuOpt-native solutions that run on GPU. 100x speedup on routing/scheduling tasks.

---

#### 13. `accelerated-computing-cudf`
**Skills:** GPU DataFrames, pandas acceleration, dask-cuDF, ETL, joins, groupby, CSV/Parquet I/O.

**Cluster:** `UltraMagnus`, `Wheeljack`

**Load when:** Target project has pandas DataFrames, ETL pipelines, or data processing at scale.

**Effect:** UltraMagnus replaces `pd.read_csv()` with `cudf.read_csv()` and writes GPU-accelerated DataFrame ops. Wheeljack refactors existing pandas code to cuDF. On large datasets this isn't a nice-to-have — it's orders of magnitude faster.

---

#### 14. `nemo-automodel-recipe-development` + `nemo-automodel-distributed-training`
**Skills:** YAML recipe structure, distributed training strategies (FSDP2, Megatron FSDP, DDP, parallelism settings).

**Cluster:** `UltraMagnus`, `Soundwave`

**Load when:** Target project involves training or fine-tuning models at scale, multi-GPU work.

**Effect:** Instead of hand-rolling distributed training configs, UltraMagnus writes NeMo-native recipes with correct parallelism settings for the target hardware.

---

#### 15. `physical-ai-infrastructure-setup-and-resilient-scaling`
**Skills:** MicroK8s/Azure AKS setup, Kubernetes clusters, inference endpoint deployment, OSMO, scaling.

**Cluster:** `UltraMagnus`, `Soundwave` (infrastructure cluster)

**Load when:** Target project needs Kubernetes deployment, inference serving, or physical AI infrastructure.

**Effect:** UltraMagnus writes production-grade K8s manifests and OSMO workflow configs instead of generic Docker Compose files.

---

#### 16. `holoscan-setup` + `holoscan-install-*`
**Skills:** Holoscan SDK — video analytics pipelines, GStreamer, TensorRT inference, object detection/tracking.

**Cluster:** `UltraMagnus`

**Load when:** Target project involves real-time video processing, edge AI, or sensor fusion.

**Effect:** UltraMagnus writes Holoscan-native operator graphs instead of raw OpenCV/GStreamer pipelines.

---

#### 17. `cudaq-guide`
**Skills:** CUDA-Q, quantum circuit simulation, QPU hardware, quantum applications.

**Cluster:** `Perceptor` (new specialized cluster if needed)

**Load when:** Target project involves quantum computing simulation or hybrid quantum-classical algorithms.

**Effect:** This is a niche but complete unlock. Without this skill, no current LLM writes correct CUDA-Q code reliably. With it, you have the only autonomous coding swarm that can target quantum hardware.

---

## Skills That Are NOT Useful for Autobots

Skip these. Injecting them wastes context window tokens.

| Skill | Why Not |
|---|---|
| `cuopt-install` | Installation docs, not code generation knowledge |
| `nemoclaw-user-configure-security` | NemoClaw-specific security policy, not transferable |
| `nemoclaw-user-manage-sandboxes` | Operational docs for NemoClaw admins |
| `nemoclaw-user-manage-policy` | Network egress policy for NemoClaw, irrelevant |
| `digital-health-clinical-asr-*` | Clinical ASR flywheel, highly domain-specific |
| `dicom-*` | DICOM medical imaging, only useful for medical projects |
| `nv-generate-*` / `nv-segment-*` | Synthetic medical imaging, irrelevant |
| `nv-reason-cxr` | Chest X-ray reasoning, irrelevant |
| `omniverse-*` | 3D/USD simulation, irrelevant unless target is Omniverse |
| `physicsnemo-discover` | SciML/physics simulation, irrelevant |
| `earth2studio-*` | Weather forecasting models, irrelevant |
| `physical-ai-video-data-augmentation` | Video data augmentation for synthetic datasets |
| `physical-ai-defect-image-generation` | Defect image generation for PCBAs |
| `mcore-*` | Megatron-LM core development, not user-facing |
| `nemo-mbridge-*` | Megatron Bridge deep internals, not needed for code gen |
| `dali-dynamic-mode` | DALI pipeline internals, too specialized |
| `skill-card-generator` | Governance tooling, not code generation |
| `cuopt-skill-evolution` | **Exception: use as universal suffix (see Tier 1)** |

---

## How to Implement This in Autobots

### Step 1 — Add `nvidia_skills/` to the skills loader

```python
# skills/loader.py — extend load_skill_pack()

NVIDIA_SKILLS_DIR = Path(__file__).parent / "nvidia"

# Map: cluster_name → list of nvidia skill filenames to always inject
CLUSTER_NVIDIA_SKILLS = {
    "Optimus": [
        "agent-skills.md",
        "autonomous-agent-research.md",
        "session-memory.md",
    ],
    "UltraMagnus": [
        "rag-blueprint.md",
        "dynamo-router.md",
        "retrieval.md",
    ],
    "Jazz": [
        "rag-eval.md",
    ],
    "Ironhide": [
        "safety-policy.md",
    ],
    "Wheeljack": [
        "dynamo-deployment.md",
    ],
}

# Universal suffix — appended to ALL clusters
UNIVERSAL_SUFFIX_SKILLS = [
    "skill-evolution.md",  # cuopt-skill-evolution
]

def load_nvidia_skills(cluster_name: str) -> str:
    if not NVIDIA_SKILLS_DIR.exists():
        return ""
    
    sections = []
    filenames = CLUSTER_NVIDIA_SKILLS.get(cluster_name, []) + UNIVERSAL_SUFFIX_SKILLS
    
    for filename in filenames:
        path = NVIDIA_SKILLS_DIR / filename
        if path.exists():
            content = path.read_text(encoding="utf-8-sig")
            sections.append(f"## NVIDIA Skill: {filename}\n\n{content}")
    
    return "\n\n---\n\n".join(sections)
```

### Step 2 — Conditional skill loading based on roadmap

```python
# skills/loader.py — detect what the project needs from roadmap

TASK_KEYWORD_TO_SKILL = {
    "rag": ["rag-blueprint.md", "rag-eval.md"],
    "retrieval": ["retrieval.md", "rag-blueprint.md"],
    "fine-tun": ["nemotron-customize.md"],
    "train": ["nemo-automodel-recipe.md", "nemo-automodel-distributed.md"],
    "routing": ["cuopt-routing.md"],
    "schedul": ["cuopt-optimization.md"],
    "dataframe": ["cudf.md"],
    "pandas": ["cudf.md"],
    "kubernetes": ["physical-ai-infra.md"],
    "deploy": ["dynamo-deployment.md"],
    "video": ["holoscan.md"],
    "quantum": ["cudaq.md"],
}

def detect_skills_from_roadmap(roadmap_text: str) -> list[str]:
    """
    Scan roadmap.md task descriptions for keywords.
    Return list of nvidia skill filenames to inject for this project.
    """
    roadmap_lower = roadmap_text.lower()
    skills_needed = set()
    
    for keyword, skill_files in TASK_KEYWORD_TO_SKILL.items():
        if keyword in roadmap_lower:
            skills_needed.update(skill_files)
    
    return list(skills_needed)
```

### Step 3 — Populate `skills/nvidia/` from the skill docs

Each NVIDIA skill doc you want to use: copy the relevant knowledge sections into a corresponding `.md` file in `autobots/skills/nvidia/`. Keep only the parts useful for code generation — strip install instructions, strip admin procedures, keep API shapes, architectural patterns, and code examples.

You don't need to copy the full 200-300 line skill docs. A tight 30-50 line extract of the most relevant API patterns and constraints is enough. The model fills in the rest from its training data. You're providing the *frame*, not an encyclopedia.

---

## The Before/After

| Cluster | Without NVIDIA Skills | With NVIDIA Skills |
|---|---|---|
| Optimus (orchestrator) | Plans tasks generically | Plans tasks using NVIDIA's documented agent lifecycle patterns |
| UltraMagnus (backend) | Writes generic FastAPI + SQLAlchemy | Writes NIM-native, RAG-Blueprint-aligned, cuDF-accelerated code |
| Jazz (test) | Writes pytest unit tests | Writes RAGAS-aligned quality evaluations for RAG, cuOpt benchmark harnesses |
| Ironhide (security) | Freeform security review | Structured Nemotron-policy-aligned reviews with JSON taxonomy |
| Wheeljack (refactor) | Generic refactoring | cuDF migration, Dynamo-native routing rewrites |

---

## Summary: The 17 That Matter

| # | Skill | Tier | Cluster | Load |
|---|---|---|---|---|
| 1 | `nemoclaw-user-agent-skills` | 🔴 Core | Optimus, UltraMagnus | Always |
| 2 | `nemo-rl-auto-research` | 🔴 Core | Optimus, Wheeljack | Always |
| 3 | `nemo-rl-session-memory` | 🔴 Core | Optimus, Jazz | Always |
| 4 | `cuopt-skill-evolution` | 🔴 Core | ALL (universal suffix) | Always |
| 5 | `nemotron-policy-generator` | 🔴 Core | Ironhide | Always |
| 6 | `rag-blueprint` | 🔴 Core | UltraMagnus, Optimus | Always |
| 7 | `rag-eval` | 🔴 Core | Jazz | Always |
| 8 | `dynamo-recipe-runner` | 🔴 Core | UltraMagnus, Wheeljack | Always |
| 9 | `dynamo-router-starter` | 🔴 Core | UltraMagnus, Optimus | Always |
| 10 | `nemo-retriever` | 🔴 Core | UltraMagnus | Always |
| 11 | `nemotron-customize` | 🟡 Conditional | UltraMagnus | If: fine-tuning/training |
| 12 | `cuopt-routing-api-python` | 🟡 Conditional | UltraMagnus | If: routing/scheduling |
| 13 | `cuopt-numerical-optimization-api-python` | 🟡 Conditional | UltraMagnus | If: LP/MILP/QP |
| 14 | `accelerated-computing-cudf` | 🟡 Conditional | UltraMagnus, Wheeljack | If: pandas/DataFrames |
| 15 | `nemo-automodel-recipe-development` | 🟡 Conditional | UltraMagnus | If: training at scale |
| 16 | `physical-ai-infrastructure-setup-and-resilient-scaling` | 🟡 Conditional | UltraMagnus | If: Kubernetes/K8s |
| 17 | `cudaq-guide` | 🟡 Conditional | Perceptor (new) | If: quantum computing |

---

## One More Thing — The Meta-Skill

`cuopt-skill-evolution` is the sleeper in this list. It's not about cuOpt. It's a **self-improvement protocol** — after each non-trivial task, the cluster reflects and proposes skill updates. Applied universally across all 9 clusters, it means:

> Every project Autobots touches makes the swarm slightly better at future projects of the same type.

That's not a 100→1000 improvement. That's compounding. That's what makes an autonomous coding swarm actually autonomous over time.
