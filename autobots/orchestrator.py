"""Mark I/II — Multi-model swarm pipeline.

Mark I: Single model per subtask (original, proven with todo app).
Mark II: Dual-model collaboration per subtask (generator + reviewer).

Architecture:
- 1 Planner model decomposes task → assigns model pairs to subtasks
- N Worker pairs execute in parallel, each with generator + reviewer
- Shared context markdown coordinates types, imports, and design language
- Repair phase detects missing files, fixes imports, and retries on failure
- Rate limiter enforces NVIDIA NIM free tier limits (40 calls/min)

Models used:
- qwen/qwen3-next-80b-a3b-instruct: planner + UI/test generation
- meta/llama-3.3-70b-instruct: logic generation + review

All API responses are logged to logs/ directory.
"""

import json, os, re, time, threading, logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed


# ── Logging Setup ──────────────────────────────────────────────────────────

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Create timestamped log file
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = LOG_DIR / f"orchestrator_{timestamp}.log"

# Setup file logger
file_handler = logging.FileHandler(log_file, encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

# Setup console logger
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter("%(message)s"))

logger = logging.getLogger("mark1")
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)
logger.addHandler(console_handler)


# ── Model Catalog ──────────────────────────────────────────────────────────

MODELS = {
    # UI / Design
    "ui": {"id": "qwen/qwen3-next-80b-a3b-instruct", "desc": "UI components"},
    "ui-fast": {"id": "qwen/qwen3-next-80b-a3b-instruct", "desc": "Fast UI boilerplate"},

    # Business Logic
    "logic": {"id": "qwen/qwen3-next-80b-a3b-instruct", "desc": "Core business logic"},
    "logic-fast": {"id": "qwen/qwen3-next-80b-a3b-instruct", "desc": "Boilerplate + CRUD"},

    # Tests
    "tests": {"id": "meta/llama-3.3-70b-instruct", "desc": "Unit tests"},

    # Safety
    "safety": {"id": "nvidia/nemotron-3-content-safety", "desc": "Security audit"},

    # Planning
    "planner": {"id": "qwen/qwen3-next-80b-a3b-instruct", "desc": "Task decomposition"},

    # Fast / Cheap
    "fast": {"id": "qwen/qwen3-next-80b-a3b-instruct", "desc": "Quick tasks"},
}

# Task type → model mapping
TASK_MODEL_MAP = {
    "ui-component": "ui",
    "ui-style": "ui",
    "ui-layout": "ui",
    "api-endpoint": "logic",
    "business-logic": "logic",
    "data-model": "logic",
    "database": "logic",
    "unit-test": "tests",
    "integration-test": "tests",
    "security-audit": "safety",
    "input-validation": "safety",
    "boilerplate": "logic-fast",
    "config": "fast",
    "documentation": "fast",
}


# ── Mark II: Dual-Model Pairs ──────────────────────────────────────────────
# Each role has a generator (creates code) and reviewer (validates + fixes).
# Two different models catch each other's blind spots.
# KEY: Both models MUST return valid JSON. Llama-3.3-70b fails this requirement.

MODEL_PAIRS = {
    "ui": {
        "generator": "qwen/qwen3-next-80b-a3b-instruct",
        "reviewer": "qwen/qwen3.5-122b-a10b",
        "desc": "UI: Qwen-80b generates design, Qwen-122b reviews (different size catches different issues)",
    },
    "logic": {
        "generator": "qwen/qwen3.5-122b-a10b",
        "reviewer": "qwen/qwen3-next-80b-a3b-instruct",
        "desc": "Logic: Qwen-122b generates types, Qwen-80b reviews edge cases",
    },
    "tests": {
        "generator": "qwen/qwen3-next-80b-a3b-instruct",
        "reviewer": "meta/llama-3.3-70b-instruct",
        "desc": "Tests: Qwen generates test structure, Llama reviews logic (OK for review-only)",
    },
    "fast": {
        "generator": "qwen/qwen3-next-80b-a3b-instruct",
        "reviewer": "stepfun-ai/step-3.5-flash",
        "desc": "Config: Qwen generates, Step-Flash validates (fastest model)",
    },
}

TASK_PAIR_MAP = {
    "ui-component": "ui",
    "ui-style": "ui",
    "ui-layout": "ui",
    "api-endpoint": "logic",
    "business-logic": "logic",
    "data-model": "logic",
    "database": "logic",
    "unit-test": "tests",
    "integration-test": "tests",
    "boilerplate": "fast",
    "config": "fast",
    "documentation": "fast",
}


# ── Rate Limiter ───────────────────────────────────────────────────────────

class RateLimiter:
    """Track API calls, enforce rate limit with spacing."""

    def __init__(self, max_per_minute=30, min_interval=3.0):
        self.max_per_minute = max_per_minute
        self.min_interval = min_interval
        self.calls = []
        self.lock = threading.Lock()

    def wait_if_needed(self):
        """Block until we can make another call."""
        with self.lock:
            now = time.time()
            # Remove calls older than 60s
            self.calls = [t for t in self.calls if now - t < 60]

            # Enforce minimum interval between calls
            if self.calls:
                elapsed = now - self.calls[-1]
                if elapsed < self.min_interval:
                    wait_time = self.min_interval - elapsed
                    logger.debug(f"[rate-limit] Spacing {wait_time:.1f}s")
                    time.sleep(wait_time)
                    now = time.time()
                    self.calls = [t for t in self.calls if now - t < 60]

            if len(self.calls) >= self.max_per_minute:
                wait_time = 60 - (now - self.calls[0]) + 0.5
                logger.debug(f"[rate-limit] Waiting {wait_time:.1f}s")
                time.sleep(wait_time)
                now = time.time()
                self.calls = [t for t in self.calls if now - t < 60]

            self.calls.append(time.time())
            logger.debug(f"[rate-limit] Calls this minute: {len(self.calls)}")

    def backoff(self):
        """Apply exponential backoff after rate limit error."""
        with self.lock:
            # Wait 30 seconds
            logger.debug(f"[rate-limit] Backoff: waiting 30s")
            time.sleep(30)
            # Remove old calls
            now = time.time()
            self.calls = [t for t in self.calls if now - t < 60]


# ── Critical Files ──────────────────────────────────────────────────────────

# Files every React project needs — planner often forgets these
CRITICAL_FILES = {
    "index.html": """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>App</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>""",
    "package.json": "",  # Generated dynamically
    "src/main.tsx": """import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)""",
    "src/index.css": """* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  -webkit-font-smoothing: antialiased;
}""",
    "vite.config.ts": """import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
})""",
    "tsconfig.json": """{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": false,
    "noUnusedParameters": false,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"]
}""",
}


def ensure_critical_files(project_path, subtasks):
    """Check if planner included critical files. Inject missing ones."""
    all_planned_files = set()
    for st in subtasks:
        all_planned_files.update(st.get("files", []))

    # Always generate package.json content
    pkg = {
        "name": "app",
        "private": True,
        "version": "0.0.0",
        "type": "module",
        "scripts": {
            "dev": "vite",
            "build": "tsc && vite build",
            "preview": "vite preview"
        },
        "dependencies": {
            "react": "^19.0.0",
            "react-dom": "^19.0.0"
        },
        "devDependencies": {
            "@types/react": "^19.0.0",
            "@types/react-dom": "^19.0.0",
            "@vitejs/plugin-react": "^4.4.1",
            "typescript": "^5.7.2",
            "vite": "^6.0.0"
        }
    }
    CRITICAL_FILES["package.json"] = json.dumps(pkg, indent=2)

    missing = []
    for filename, content in CRITICAL_FILES.items():
        if filename not in all_planned_files:
            missing.append(filename)

    if missing:
        logger.info(f"[planner] Missing critical files: {missing}")

        # Create a new subtask for missing critical files
        inject_files = []
        for f in missing:
            content = CRITICAL_FILES.get(f, "")
            if content:
                inject_files.append(f)

        if inject_files:
            inject_subtask = {
                "description": "Critical project files (auto-injected)",
                "files": inject_files,
                "task_type": "boilerplate",
                "depends_on": [],
                "model": MODELS["fast"]["id"],
                "model_key": "fast",
                "injected": True,
            }
            subtasks.insert(0, inject_subtask)
            logger.info(f"[planner] Injected subtask with {len(inject_files)} critical files")

    return subtasks


# ── Shared Context ─────────────────────────────────────────────────────────

def build_shared_context(goal, subtasks):
    """Build compact shared context for workers."""
    files_plan = []
    for i, st in enumerate(subtasks):
        files = ", ".join(st.get("files", []))
        files_plan.append(f"{i+1}. {files}")

    return f"""Project: {goal}

Files being built:
{chr(10).join(files_plan)}

TYPE CONTRACTS (ALL workers must use these exact types):
--- src/types/Todo.ts ---
export interface Todo {{
  id: string;
  text: string;
  completed: boolean;
  createdAt: Date;
}}
export type FilterType = 'all' | 'active' | 'completed';

--- src/hooks/useTodos.ts (MUST export these) ---
export function useTodos() {{
  return {{
    todos: Todo[],           // filtered list based on current filter
    filter: FilterType,
    setFilter: (f: FilterType) => void,
    addTodo: (text: string) => void,         // takes a STRING, not an object
    toggleTodo: (id: string) => void,        // takes string ID
    deleteTodo: (id: string) => void,        // takes string ID
    remainingCount: number,
  }};
}}

--- Component Prop Contracts (use EXACTLY these signatures) ---
TodoInput: {{ onAddTodo: (text: string) => void }}
TodoItem: {{ todo: Todo; onToggle: (id: string) => void; onDelete: (id: string) => void }}
TodoFilter: {{ filter: FilterType; setFilter: (f: FilterType) => void }}
TodoCounter: {{ count: number }}

DESIGN LANGUAGE (apply to all UI):
- Colors: cohesive palette (blues #3b82f6/#60a5fa/#1e40af, or slates #0f172a/#1e293b/#334155)
- Shadows: 0 4px 6px -1px rgba(0,0,0,0.1) for cards, 0 10px 15px -3px for modals
- Transitions: all 0.2s ease on hover/focus
- Typography: font-weight 600-700 headings, 14-16px body
- Spacing: 16-24px padding, 8-12px gap in flex/grid
- Border-radius: 8-12px for cards, 6px for buttons, 50% for circles
- Gradients: linear-gradient(135deg, start, end) for accents

CODE RULES:
- React functional components with hooks
- Export default for main components
- Import React in files that use JSX
- Import Todo from '../types/Todo' (or '../types') where needed

Return JSON: {{"files": [{{"path": "...", "content": "..."}}]}}"""


# ── JSON Parser ────────────────────────────────────────────────────────────

def parse_json_response(content, context=""):
    """Parse JSON from model response, handling common issues."""
    logger.debug(f"[json] Parsing response ({len(content)} chars) {context}")

    if not content or not content.strip():
        logger.debug(f"[json] Empty response")
        return None

    # Strip markdown code fences (multiple patterns)
    content = re.sub(r"```json\s*", "", content)
    content = re.sub(r"```\s*$", "", content)
    content = re.sub(r"```\s*", "", content)
    content = re.sub(r"^```.*$", "", content, flags=re.MULTILINE)

    # Strip common prefixes/suffixes models add
    content = re.sub(r"^(Here\s+(is|are)|Below\s+is|The\s+JSON|Response:?)\s*:?\s*", "", content, flags=re.IGNORECASE)
    content = re.sub(r"\s*(Hope\s+this\s+helps|Let\s+me\s+know).*$", "", content, flags=re.IGNORECASE)

    # Try to find JSON object (greedy match)
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if not match:
        # Model returned code blocks instead of JSON — wrap them
        code_block = re.search(r"(?:typescript|javascript|ts|js)\s*\n(.*?)$", content, re.DOTALL)
        if code_block:
            code = code_block.group(1).strip()
            # Try to infer path from comment
            path_match = re.search(r"//\s*(src/\S+)", code)
            path = path_match.group(1) if path_match else "src/unknown.ts"
            logger.debug(f"[json] Found code block instead of JSON, wrapping as files entry")
            return {"files": [{"path": path, "content": code}]}
        logger.debug(f"[json] No JSON object found in: {content[:300]}")
        return None

    raw = match.group()
    logger.debug(f"[json] Raw JSON ({len(raw)} chars): {raw[:200]}...")

    # Try direct parse with strict=False to allow control characters in strings
    try:
        data = json.loads(raw, strict=False)
        logger.debug(f"[json] Direct parse succeeded (strict=False)")
        return data
    except json.JSONDecodeError as e:
        logger.debug(f"[json] Direct parse failed: {e}")

    # Try fixing common issues
    fixes = [
        ("remove_newlines", lambda s: s.replace('\n', '\\n')),
        ("remove_carriage_returns", lambda s: s.replace('\r', '')),
        ("remove_tabs", lambda s: s.replace('\t', '\\t')),
        ("fix_single_quotes", lambda s: s.replace("'", '"')),
        ("fix_trailing_commas", lambda s: re.sub(r",\s*([}\]])", r"\1", s)),
        ("fix_double_escaped", lambda s: s.replace('\\\\n', '\\n')),
    ]

    for name, fix in fixes:
        try:
            fixed = fix(raw)
            data = json.loads(fixed)
            logger.debug(f"[json] Fixed parse succeeded with: {name}")
            return data
        except json.JSONDecodeError:
            continue

    # Try to extract files array specifically
    files_match = re.search(r'"files"\s*:\s*\[.*?\]', raw, re.DOTALL)
    if files_match:
        try:
            data = json.loads("{" + files_match.group() + "}")
            logger.debug(f"[json] Extracted files array successfully")
            return data
        except json.JSONDecodeError:
            pass

    logger.debug(f"[json] All parse attempts failed. Raw content: {raw[:500]}")
    return None


# ── Planner ────────────────────────────────────────────────────────────────

def plan_subtasks(goal, rate_limiter):
    """Use planner model to decompose goal into subtasks with model assignments."""
    logger.info(f"\n[PLANNER] Decomposing: {goal}")

    rate_limiter.wait_if_needed()

    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=os.environ.get("NVIDIA_API_KEY", ""),
    )

    system = """You are a project planner. Decompose a goal into subtasks.

For each subtask, specify:
- description: what to build
- files: list of file paths to generate (1-2 files max per subtask)
- task_type: one of ui-component, ui-style, api-endpoint, business-logic, unit-test, boilerplate, config
- depends_on: list of subtask indices this depends on (empty if independent)

Return JSON: {"subtasks": [{"description": "...", "files": ["..."], "task_type": "...", "depends_on": []}]}

Rules:
- Each subtask gets 1-2 files max
- Independent subtasks should have empty depends_on
- Group related files (App.tsx + App.css together)
- Include at least one test subtask
- Include config/boilerplate subtask"""

    user = f"Goal: {goal}\n\nDecompose into subtasks."

    try:
        logger.debug(f"[planner] Calling {MODELS['planner']['id']}")
        start = time.time()

        r = client.chat.completions.create(
            model=MODELS["planner"]["id"],
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=4096, temperature=0.3, timeout=120,
        )

        elapsed = time.time() - start
        content = r.choices[0].message.content or ""
        logger.debug(f"[planner] Response in {elapsed:.1f}s: {content[:500]}")

        # Log full response
        with open(LOG_DIR / f"planner_response_{timestamp}.json", "w", encoding="utf-8") as f:
            json.dump({
                "model": MODELS["planner"]["id"],
                "elapsed": elapsed,
                "content": content,
                "finish_reason": r.choices[0].finish_reason,
            }, f, indent=2, ensure_ascii=False)

        # Parse JSON
        data = parse_json_response(content, "planner")
        if data and "subtasks" in data:
            subtasks = data["subtasks"]
            logger.info(f"[planner] Found {len(subtasks)} subtasks")

            # Assign models based on task_type
            for st in subtasks:
                task_type = st.get("task_type", "boilerplate")
                model_key = TASK_MODEL_MAP.get(task_type, "fast")
                st["model"] = MODELS[model_key]["id"]
                st["model_key"] = model_key

            # Remove duplicate file assignments
            seen_files = set()
            unique_subtasks = []
            for st in subtasks:
                files = st.get("files", [])
                new_files = [f for f in files if f not in seen_files]
                if new_files:
                    seen_files.update(new_files)
                    st["files"] = new_files
                    unique_subtasks.append(st)

            subtasks = unique_subtasks

            for i, st in enumerate(subtasks):
                files = ", ".join(st.get("files", []))
                model = st.get("model", "unknown").split("/")[-1]
                logger.info(f"  {i+1}. [{model}] {files}")

            return subtasks
        else:
            logger.error(f"[planner] Failed to parse subtasks")
            return []

    except Exception as e:
        logger.error(f"[planner] Error: {e}")
        return []


# ── Worker ─────────────────────────────────────────────────────────────────

def execute_worker(idx, model_id, task_desc, shared_context, files_to_build, rate_limiter):
    """Execute a single worker: call model, generate 1-2 files."""
    logger.info(f"[worker-{idx}] Starting: {files_to_build} using {model_id.split('/')[-1]}")

    rate_limiter.wait_if_needed()

    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=os.environ.get("NVIDIA_API_KEY", ""),
    )

    # Design-aware prompt for UI files
    is_ui = any("component" in f.lower() or "style" in f.lower() or f.endswith(".css") for f in files_to_build)

    if is_ui:
        system = f"""Build these files: {', '.join(files_to_build)}

Context: {shared_context}

DESIGN RULES (UI files must look professional):
- Use modern CSS: flexbox/grid, gap, rounded corners, smooth transitions
- Colors: use a cohesive palette (e.g. blues: #3b82f6, #60a5fa, #1e40af)
- Add hover effects on buttons (transform, shadow changes)
- Use box-shadow for depth: 0 4px 6px -1px rgba(0,0,0,0.1)
- Typography: font-weight 600-700 for headings, proper line-height
- Transitions: all 0.2s ease on interactive elements
- Dark backgrounds: use #0f172a, #1e293b, #334155 (slate scale)
- Light backgrounds: use #f8fafc, #f1f5f9, #e2e8f0
- Gradient accents: linear-gradient(135deg, color1, color2)
- Glass effect: background rgba(255,255,255,0.1) + backdrop-filter: blur(10px)
- Spacing: generous padding (16px-24px), consistent margins
- Responsive: use %, rem, or vh/vw units

Return JSON: {{"files": [{{"path": "src/...", "content": "full code here"}}]}}"""
    else:
        system = f"""Build these files: {', '.join(files_to_build)}

Context: {shared_context}

CODE RULES:
- Clean, well-structured code
- TypeScript types where applicable
- React: use functional components with hooks
- Export default for main components

Return JSON: {{"files": [{{"path": "src/...", "content": "full code here"}}]}}"""

    try:
        start = time.time()
        logger.debug(f"[worker-{idx}] Calling {model_id}")

        # Retry logic for rate limits and timeouts
        max_retries = 3
        for attempt in range(max_retries):
            try:
                r = client.chat.completions.create(
                    model=model_id,
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": task_desc}],
                    max_tokens=4096, temperature=0.3, timeout=120,
                )
                break
            except Exception as e:
                if ("429" in str(e) or "timed out" in str(e).lower() or "DEGRADED" in str(e)) and attempt < max_retries - 1:
                    logger.warning(f"[worker-{idx}] Failed ({type(e).__name__}), retrying (attempt {attempt + 1})")
                    rate_limiter.backoff()
                    continue
                raise

        elapsed = time.time() - start
        content = r.choices[0].message.content or ""
        logger.debug(f"[worker-{idx}] Response in {elapsed:.1f}s: {content[:300]}")

        # Log full response
        with open(LOG_DIR / f"worker_{idx}_response_{timestamp}.json", "w", encoding="utf-8") as f:
            json.dump({
                "model": model_id,
                "task": task_desc,
                "files": files_to_build,
                "elapsed": elapsed,
                "content": content,
                "finish_reason": r.choices[0].finish_reason,
            }, f, indent=2, ensure_ascii=False)

        # Parse JSON
        data = parse_json_response(content, f"worker-{idx}")
        if data and "files" in data:
            files = data["files"]
            # Filter to only include requested files
            requested_set = set(files_to_build)
            filtered = [f for f in files if f.get("path", "") in requested_set]
            
            if len(filtered) < len(files):
                logger.info(f"[worker-{idx}] Filtered {len(files)} -> {len(filtered)} files (kept only requested)")
            
            logger.info(f"[worker-{idx}] Generated {len(filtered)} files in {elapsed:.1f}s")
            return filtered
        else:
            logger.error(f"[worker-{idx}] Failed to parse response")
            return []

    except Exception as e:
        logger.error(f"[worker-{idx}] Error: {e}")
        return []


# ── Mark II: Dual-Model Worker ─────────────────────────────────────────────

def execute_worker_v2(idx, generator_id, reviewer_id, task_desc, shared_context,
                      files_to_build, rate_limiter):
    """Dual-model worker: Generator creates → Reviewer validates + fixes.

    Flow:
    1. Generator model builds the files
    2. Reviewer model receives draft + context, checks for errors
    3. If reviewer finds issues, it returns fixed files
    4. Final output is written to disk
    """
    gen_name = generator_id.split("/")[-1]
    rev_name = reviewer_id.split("/")[-1]
    logger.info(f"[worker-v2-{idx}] Starting: {files_to_build}")
    logger.info(f"[worker-v2-{idx}] Generator: {gen_name} | Reviewer: {rev_name}")

    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=os.environ.get("NVIDIA_API_KEY", ""),
    )

    # ── Step 1: Generator creates files ──
    is_ui = any("component" in f.lower() or "style" in f.lower() or f.endswith(".css") for f in files_to_build)

    if is_ui:
        gen_system = f"""Build these files: {', '.join(files_to_build)}

Context: {shared_context}

DESIGN RULES (UI files must look professional):
- Use modern CSS: flexbox/grid, gap, rounded corners, smooth transitions
- Colors: use a cohesive palette (e.g. blues: #3b82f6, #60a5fa, #1e40af)
- Add hover effects on buttons (transform, shadow changes)
- Use box-shadow for depth: 0 4px 6px -1px rgba(0,0,0,0.1)
- Typography: font-weight 600-700 for headings, proper line-height
- Transitions: all 0.2s ease on interactive elements
- Dark backgrounds: use #0f172a, #1e293b, #334155 (slate scale)
- Light backgrounds: use #f8fafc, #f1f5f9, #e2e8f0
- Gradient accents: linear-gradient(135deg, color1, color2)
- Glass effect: background rgba(255,255,255,0.1) + backdrop-filter: blur(10px)
- Spacing: generous padding (16px-24px), consistent margins
- Responsive: use %, rem, or vh/vw units

IMPORTANT: You MUST reply with valid JSON only. No explanations, no markdown, no code blocks.
Reply with this exact format: {{"files": [{{"path": "src/...", "content": "full code here"}}]}}"""
    else:
        gen_system = f"""Build these files: {', '.join(files_to_build)}

Context: {shared_context}

CODE RULES:
- Clean, well-structured code
- TypeScript types where applicable
- React: use functional components with hooks
- Export default for main components

IMPORTANT: You MUST reply with valid JSON only. No explanations, no markdown, no code blocks.
Reply with this exact format: {{"files": [{{"path": "src/...", "content": "full code here"}}]}}"""

    try:
        rate_limiter.wait_if_needed()
        start = time.time()
        logger.debug(f"[worker-v2-{idx}] Generator calling {generator_id}")

        max_retries = 3
        for attempt in range(max_retries):
            try:
                r = client.chat.completions.create(
                    model=generator_id,
                    messages=[{"role": "system", "content": gen_system}, {"role": "user", "content": task_desc}],
                    max_tokens=4096, temperature=0.3, timeout=120,
                )
                break
            except Exception as e:
                if ("429" in str(e) or "timed out" in str(e).lower() or "DEGRADED" in str(e)) and attempt < max_retries - 1:
                    logger.warning(f"[worker-v2-{idx}] Generator failed, retrying (attempt {attempt + 1})")
                    rate_limiter.backoff()
                    continue
                raise

        gen_elapsed = time.time() - start
        gen_content = r.choices[0].message.content or ""
        logger.debug(f"[worker-v2-{idx}] Generator done in {gen_elapsed:.1f}s")

        # Log generator response
        with open(LOG_DIR / f"worker_v2_{idx}_gen_{timestamp}.json", "w", encoding="utf-8") as f:
            json.dump({
                "step": "generator",
                "model": generator_id,
                "elapsed": gen_elapsed,
                "content": gen_content,
            }, f, indent=2, ensure_ascii=False)

        gen_data = parse_json_response(gen_content, f"worker-v2-{idx}-gen")
        if not gen_data or "files" not in gen_data:
            logger.error(f"[worker-v2-{idx}] Generator failed to parse response")
            return []

        gen_files = gen_data["files"]
        requested_set = set(files_to_build)
        gen_files = [f for f in gen_files if f.get("path", "") in requested_set]

        if not gen_files:
            logger.error(f"[worker-v2-{idx}] Generator returned no valid files")
            return []

        logger.info(f"[worker-v2-{idx}] Generator produced {len(gen_files)} files in {gen_elapsed:.1f}s")

    except Exception as e:
        logger.error(f"[worker-v2-{idx}] Generator error: {e}")
        return []

    # ── Step 2: Reviewer validates + fixes ──
    gen_files_text = "\n\n".join(
        f"--- {f['path']} ---\n{f['content']}" for f in gen_files
    )

    rev_system = f"""You are a code reviewer. Review these generated files for errors.

Context: {shared_context}

Check for:
- TypeScript type errors or mismatches
- Missing imports or wrong import paths
- Incorrect component prop signatures
- Broken references between files
- CSS issues (wrong selectors, missing styles)
- Logic bugs or incorrect function signatures
- Missing exports

RULES:
- If files are good, return status "pass" with the original files unchanged
- If issues found, return status "revise" with FIXED versions of the files
- Fix ONLY what's broken. Do not rewrite working code.
- Return ALL files (both fixed and unchanged)

Return JSON: {{"status": "pass"|"revise", "issues": ["issue 1"], "files": [{{"path": "src/...", "content": "file content"}}]}}"""

    rev_user = f"Review these files for errors:\n\n{gen_files_text}"

    try:
        rate_limiter.wait_if_needed()
        rev_start = time.time()
        logger.debug(f"[worker-v2-{idx}] Reviewer calling {reviewer_id}")

        for attempt in range(max_retries):
            try:
                r2 = client.chat.completions.create(
                    model=reviewer_id,
                    messages=[{"role": "system", "content": rev_system}, {"role": "user", "content": rev_user}],
                    max_tokens=4096, temperature=0.2, timeout=120,
                )
                break
            except Exception as e:
                if ("429" in str(e) or "timed out" in str(e).lower() or "DEGRADED" in str(e)) and attempt < max_retries - 1:
                    logger.warning(f"[worker-v2-{idx}] Reviewer failed, retrying (attempt {attempt + 1})")
                    rate_limiter.backoff()
                    continue
                raise

        rev_elapsed = time.time() - rev_start
        rev_content = r2.choices[0].message.content or ""
        logger.debug(f"[worker-v2-{idx}] Reviewer done in {rev_elapsed:.1f}s")

        # Log reviewer response
        with open(LOG_DIR / f"worker_v2_{idx}_rev_{timestamp}.json", "w", encoding="utf-8") as f:
            json.dump({
                "step": "reviewer",
                "model": reviewer_id,
                "elapsed": rev_elapsed,
                "content": rev_content,
            }, f, indent=2, ensure_ascii=False)

        rev_data = parse_json_response(rev_content, f"worker-v2-{idx}-rev")
        if not rev_data or "files" not in rev_data:
            logger.warning(f"[worker-v2-{idx}] Reviewer parse failed, using generator output")
            logger.info(f"[worker-v2-{idx}] Done (gen only): {len(gen_files)} files in {gen_elapsed:.1f}s")
            return gen_files

        status = rev_data.get("status", "pass")
        issues = rev_data.get("issues", [])
        rev_files = rev_data["files"]

        # Filter reviewer output to requested files
        rev_files = [f for f in rev_files if f.get("path", "") in requested_set]

        if status == "revise" and issues:
            logger.info(f"[worker-v2-{idx}] Reviewer found {len(issues)} issues:")
            for issue in issues[:3]:
                logger.info(f"  - {issue}")

        # Use reviewer's files if they fixed something, otherwise use generator's
        final_files = rev_files if status == "revise" and rev_files else gen_files
        total_elapsed = gen_elapsed + rev_elapsed
        logger.info(f"[worker-v2-{idx}] Done: {len(final_files)} files in {total_elapsed:.1f}s (gen {gen_elapsed:.1f}s + rev {rev_elapsed:.1f}s)")

        return final_files

    except Exception as e:
        logger.error(f"[worker-v2-{idx}] Reviewer error: {e}, using generator output")
        return gen_files

def detect_missing_files(project_path, subtasks):
    """Check which expected files are missing from disk."""
    expected = set()
    for st in subtasks:
        for f in st.get("files", []):
            expected.add(f)

    missing = []
    for f in expected:
        full_path = project_path / f
        if not full_path.exists():
            missing.append(f)
        elif full_path.stat().st_size == 0:
            missing.append(f)  # Empty file is also bad

    return missing


def regenerate_missing_files(project_path, missing_files, subtasks, shared_context, rate_limiter):
    """Send missing files to model for regeneration."""
    if not missing_files:
        return 0

    logger.info(f"[repair] Regenerating {len(missing_files)} missing files: {missing_files}")

    # Find which subtask originally owned these files
    file_descriptions = []
    for st in subtasks:
        for f in st.get("files", []):
            if f in missing_files:
                file_descriptions.append(f"- {f}: {st.get('description', 'unknown')}")

    # Read existing files for context
    existing_files = []
    for f in project_path.rglob("src/**/*.ts*"):
        if "node_modules" in str(f):
            continue
        rel = f.relative_to(project_path).as_posix()
        content = f.read_text(encoding="utf-8")
        existing_files.append(f"--- {rel} ---\n{content[:2000]}")  # Truncate large files

    rate_limiter.wait_if_needed()

    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=os.environ.get("NVIDIA_API_KEY", ""),
    )

    system = f"""{shared_context}

You are generating missing files for this project. The following files failed to generate
due to API errors. Generate them now, following the TYPE CONTRACTS above exactly.

Return JSON: {{"files": [{{"path": "src/...", "content": "full file content"}}]}}"""

    user = f"""Missing files to generate:
{chr(10).join(file_descriptions)}

Existing files for reference:
{chr(10).join(existing_files[:5])}

Generate the missing files. Follow the TYPE CONTRACTS from the context exactly."""

    try:
        start = time.time()
        r = client.chat.completions.create(
            model=MODELS["fast"]["id"],
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=8192, temperature=0.3, timeout=120,
        )
        elapsed = time.time() - start
        content = r.choices[0].message.content or ""

        # Log response
        with open(LOG_DIR / f"regen_response_{timestamp}.json", "w", encoding="utf-8") as f:
            json.dump({
                "model": MODELS["fast"]["id"],
                "elapsed": elapsed,
                "missing_files": missing_files,
                "content": content,
            }, f, indent=2, ensure_ascii=False)

        # Parse and write
        data = parse_json_response(content, "regen")
        if data and "files" in data:
            written = 0
            for file_data in data["files"]:
                path = file_data.get("path", "")
                file_content = file_data.get("content", "")
                if path and file_content and path in missing_files:
                    target = project_path / path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(file_content, encoding="utf-8")
                    logger.info(f"[repair] Generated {path}")
                    written += 1
            return written
        else:
            logger.warning("[repair] Failed to parse regen response")
            return 0

    except Exception as e:
        logger.error(f"[repair] Regen error: {e}")
        return 0


def repair_phase(project_path, rate_limiter, subtasks=None, shared_context=""):
    """Run TypeScript check, detect missing files, send errors to model for repair."""
    import subprocess
    total_repaired = 0

    # Step 0: Detect and regenerate missing files
    if subtasks:
        missing = detect_missing_files(project_path, subtasks)
        if missing:
            logger.info(f"[repair] Detected {len(missing)} missing files")
            regenerated = regenerate_missing_files(
                project_path, missing, subtasks, shared_context, rate_limiter
            )
            total_repaired += regenerated
            logger.info(f"[repair] Regenerated {regenerated} files")

    # Step 1: Run TypeScript check
    logger.info("[repair] Running TypeScript check...")
    try:
        # Use npx.cmd on Windows, npx on Unix
        npx_cmd = "npx.cmd" if os.name == "nt" else "npx"
        result = subprocess.run(
            [npx_cmd, "tsc", "--noEmit"],
            cwd=str(project_path),
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0:
            logger.info("[repair] TypeScript check passed")
            return total_repaired
        errors = result.stdout + result.stderr
    except Exception as e:
        logger.warning(f"[repair] TypeScript check failed: {e}")
        # Fallback: detect common issues by parsing files
        return total_repaired + repair_by_parsing(project_path, rate_limiter)

    # Step 2: Parse errors
    error_lines = [l for l in errors.split("\n") if l.startswith("src/") and "error TS" in l]
    if not error_lines:
        logger.info("[repair] No TypeScript errors found")
        return total_repaired

    logger.info(f"[repair] Found {len(error_lines)} TypeScript errors")
    for line in error_lines[:5]:
        logger.info(f"  {line}")

    # Step 3: Collect affected files
    affected_files = set()
    for line in error_lines:
        parts = line.split("(")
        if parts:
            filepath = parts[0].strip()
            affected_files.add(filepath)

    # Read file contents
    files_content = []
    for f in affected_files:
        full_path = project_path / f
        if full_path.exists():
            content = full_path.read_text(encoding="utf-8")
            files_content.append(f"--- {f} ---\n{content}")

    # Step 4: Send to repair model
    logger.info(f"[repair] Sending {len(affected_files)} files to repair model...")

    rate_limiter.wait_if_needed()

    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=os.environ.get("NVIDIA_API_KEY", ""),
    )

    system = """You are a TypeScript repair agent. Fix the type errors in the provided files.

RULES:
- Fix ONLY the type errors shown. Do not rewrite entire files.
- Return the COMPLETE fixed file for each file that needs changes.
- Keep the same structure and logic, only fix type mismatches.
- Common fixes: add missing imports, align interface props, fix function signatures.

IMPORTANT: Reply with valid JSON only. No markdown, no code blocks.
Return JSON: {"files": [{"path": "src/...", "content": "full fixed file content"}]}"""

    user = f"""TypeScript errors:
{chr(10).join(error_lines[:20])}

Files with errors:
{chr(10).join(files_content)}

Fix the type errors and return the fixed files."""

    try:
        start = time.time()
        r = client.chat.completions.create(
            model=MODELS["fast"]["id"],
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=8192, temperature=0.2, timeout=120,
        )
        elapsed = time.time() - start
        content = r.choices[0].message.content or ""

        # Log repair response
        with open(LOG_DIR / f"repair_response_{timestamp}.json", "w", encoding="utf-8") as f:
            json.dump({
                "model": MODELS["fast"]["id"],
                "elapsed": elapsed,
                "errors_count": len(error_lines),
                "files_affected": list(affected_files),
                "content": content,
            }, f, indent=2, ensure_ascii=False)

        # Parse and write fixed files
        data = parse_json_response(content, "repair")
        if data and "files" in data:
            repaired = 0
            for f in data["files"]:
                path = f.get("path", "")
                file_content = f.get("content", "")
                if path and file_content:
                    target = project_path / path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(file_content, encoding="utf-8")
                    logger.info(f"[repair] Fixed {path}")
                    repaired += 1
            return total_repaired + repaired
        else:
            logger.warning("[repair] Failed to parse repair response")
            return total_repaired

    except Exception as e:
        logger.error(f"[repair] Error: {e}")
        return total_repaired


def repair_by_parsing(project_path, rate_limiter):
    """Fallback: detect common issues by parsing files."""
    import re

    logger.info("[repair] Using file parsing fallback...")

    # Read all TypeScript/TSX files
    ts_files = {}
    for f in project_path.rglob("src/**/*.ts*"):
        if "node_modules" in str(f):
            continue
        rel = f.relative_to(project_path).as_posix()
        content = f.read_text(encoding="utf-8")
        ts_files[rel] = content

    if not ts_files:
        logger.info("[repair] No TypeScript files found")
        return 0

    fixed = 0

    # Fix 1: Check all import paths resolve to real files
    for path, content in ts_files.items():
        lines = content.split("\n")
        new_lines = []
        changed = False
        for line in lines:
            match = re.match(r"import\s+.*from\s+['\"](\./[^'\"]+)['\"]", line)
            if match:
                import_path = match.group(1)
                # Resolve relative to this file's directory
                file_dir = Path(path).parent
                resolved = (file_dir / import_path).as_posix()
                # Check if file exists (try .tsx, .ts, /index.tsx)
                candidates = [
                    project_path / f"{resolved}.tsx",
                    project_path / f"{resolved}.ts",
                    project_path / resolved / "index.tsx",
                    project_path / resolved / "index.ts",
                ]
                if not any(c.exists() for c in candidates):
                    # Try to find the actual file
                    basename = Path(import_path).name
                    for f in project_path.rglob(f"src/**/{basename}.tsx"):
                        actual = f.relative_to(project_path).as_posix()
                        actual_import = "./" + str(Path(actual).with_suffix("")).replace("src/", "").replace("\\", "/")
                        line = line.replace(import_path, actual_import)
                        logger.info(f"[repair] Fixed import path: {import_path} -> {actual_import} in {path}")
                        changed = True
                        break
            new_lines.append(line)
        if changed:
            full_path = project_path / path
            full_path.write_text("\n".join(new_lines), encoding="utf-8")
            fixed += 1

    # Fix 2: Check App.tsx for missing imports
    app_content = ts_files.get("src/App.tsx", "")
    if app_content:
        # Find components used but not imported
        used_components = re.findall(r"<(\w+)[\s/>]", app_content)
        imported_names = set()
        for imp in re.findall(r"import\s+(?:\{[^}]+\}|\w+)", app_content):
            for name in re.findall(r"\w+", imp):
                if name[0].isupper():
                    imported_names.add(name)

        missing_imports = []
        for comp in used_components:
            if comp[0].isupper() and comp not in imported_names and comp not in ("React",):
                missing_imports.append(comp)

        if missing_imports:
            # Try to find the component files
            for comp in missing_imports:
                # Search for component file
                for f in project_path.rglob(f"src/**/{comp}.tsx"):
                    rel = f.relative_to(project_path).as_posix()
                    import_path = rel.replace("src/", "./").replace(".tsx", "")
                    # Add import after last existing import
                    lines = app_content.split("\n")
                    last_import_idx = 0
                    for i, line in enumerate(lines):
                        if line.startswith("import "):
                            last_import_idx = i
                    lines.insert(last_import_idx + 1, f"import {comp} from '{import_path}';")
                    app_content = "\n".join(lines)
                    logger.info(f"[repair] Added missing import: {comp} from {import_path}")

            # Write fixed App.tsx
            if missing_imports:
                target = project_path / "src/App.tsx"
                target.write_text(app_content, encoding="utf-8")
                fixed += 1

    # Detect issues
    issues = []

    # Check for interface mismatches
    # Find all onAddTodo, onToggle, onDelete signatures
    signatures = {}
    for path, content in ts_files.items():
        for match in re.finditer(r"on(?:AddTodo|Toggle|Delete):\s*\(([^)]+)\)", content):
            sig = match.group(0)
            func_name = re.search(r"on\w+", sig).group(0)
            if func_name not in signatures:
                signatures[func_name] = []
            signatures[func_name].append((path, sig))

    # Check for useTodos missing filter/setFilter
    hook_content = ts_files.get("src/hooks/useTodos.ts", "")
    app_destructure = re.findall(r"const\s*\{([^}]+)\}\s*=\s*useTodos", app_content)
    if app_destructure and hook_content:
        needed = [n.strip() for n in app_destructure[0].split(",")]
        for name in needed:
            if name and name not in hook_content:
                issues.append(f"useTodos doesn't return '{name}' but App.tsx expects it")

    if not issues:
        logger.info("[repair] No issues detected by parsing")
        return fixed

    logger.info(f"[repair] Detected {len(issues)} issues:")
    for issue in issues:
        logger.info(f"  - {issue}")

    # Send to repair model
    return fixed + send_repair_request(project_path, issues, ts_files, rate_limiter)


def send_repair_request(project_path, issues, ts_files, rate_limiter):
    """Send detected issues to repair model."""
    logger.info(f"[repair] Sending {len(issues)} issues to repair model...")

    rate_limiter.wait_if_needed()

    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=os.environ.get("NVIDIA_API_KEY", ""),
    )

    # Build context with relevant files
    files_context = []
    for path in ["src/App.tsx", "src/hooks/useTodos.ts", "src/types/Todo.ts",
                 "src/components/TodoInput.tsx", "src/components/TodoItem.tsx",
                 "src/components/TodoFilter.tsx", "src/components/TodoCounter.tsx"]:
        if path in ts_files:
            files_context.append(f"--- {path} ---\n{ts_files[path]}")

    system = """You are a TypeScript repair agent. Fix the issues in the provided files.

RULES:
- Fix ONLY the issues listed. Do not rewrite entire files.
- Return the COMPLETE fixed file for each file that needs changes.
- Keep the same structure and logic, only fix the specific issues.
- Common fixes: add missing imports, align interface props, fix function signatures.

IMPORTANT: Reply with valid JSON only. No markdown, no code blocks.
Return JSON: {"files": [{"path": "src/...", "content": "full fixed file content"}]}"""

    user = f"""Issues detected:
{chr(10).join(f"- {i}" for i in issues)}

Files:
{chr(10).join(files_context)}

Fix these issues and return the fixed files."""

    try:
        start = time.time()
        r = client.chat.completions.create(
            model=MODELS["fast"]["id"],
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=8192, temperature=0.2, timeout=120,
        )
        elapsed = time.time() - start
        content = r.choices[0].message.content or ""

        # Log repair response
        with open(LOG_DIR / f"repair_response_{timestamp}.json", "w", encoding="utf-8") as f:
            json.dump({
                "model": MODELS["fast"]["id"],
                "elapsed": elapsed,
                "issues": issues,
                "content": content,
            }, f, indent=2, ensure_ascii=False)

        # Parse and write fixed files
        data = parse_json_response(content, "repair")
        if data and "files" in data:
            repaired = 0
            for file_data in data["files"]:
                path = file_data.get("path", "")
                file_content = file_data.get("content", "")
                if path and file_content:
                    target = project_path / path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(file_content, encoding="utf-8")
                    logger.info(f"[repair] Fixed {path}")
                    repaired += 1
            return repaired
        else:
            logger.warning("[repair] Failed to parse repair response")
            return 0

    except Exception as e:
        logger.error(f"[repair] Error: {e}")
        return 0


# ── Orchestrator ───────────────────────────────────────────────────────────

def orchestrate(goal, project_dir, use_v2=True):
    """Main orchestration flow.

    Args:
        goal: What to build
        project_dir: Output directory
        use_v2: If True, use Mark II dual-model (gen+review). If False, use Mark I single-model.
    """
    project_path = Path(project_dir)
    project_path.mkdir(parents=True, exist_ok=True)

    pipeline_name = "Mark II — Dual-Model Collaboration" if use_v2 else "Mark I — Single-Model Swarm"
    logger.info(f"\n{'='*60}")
    logger.info(f"{pipeline_name}")
    logger.info(f"{'='*60}")
    logger.info(f"Goal: {goal}")
    logger.info(f"Log file: {log_file}")

    # Mark II uses 2 API calls per worker, so be more conservative
    min_interval = 4.0 if use_v2 else 1.5
    rate_limiter = RateLimiter(max_per_minute=35, min_interval=min_interval)

    # Step 1: Plan subtasks
    logger.info(f"\n[1/4] Planning subtasks...")
    subtasks = plan_subtasks(goal, rate_limiter)

    if not subtasks:
        logger.error("No subtasks planned. Aborting.")
        return []

    # Step 1.5: Ensure critical files are included
    subtasks = ensure_critical_files(project_path, subtasks)

    # Step 1.6: Assign model pairs for Mark II
    if use_v2:
        for st in subtasks:
            task_type = st.get("task_type", "boilerplate")
            pair_key = TASK_PAIR_MAP.get(task_type, "fast")
            pair = MODEL_PAIRS[pair_key]
            st["generator"] = pair["generator"]
            st["reviewer"] = pair["reviewer"]
            st["pair_key"] = pair_key

        logger.info("[planner] Assigned model pairs:")
        for i, st in enumerate(subtasks):
            files = ", ".join(st.get("files", []))
            gen = st.get("generator", "?").split("/")[-1]
            rev = st.get("reviewer", "?").split("/")[-1]
            logger.info(f"  {i+1}. [{gen}+{rev}] {files}")

    # Step 2: Build shared context
    logger.info(f"\n[2/4] Building shared context...")
    shared_context = build_shared_context(goal, subtasks)
    context_file = project_path / "SHARED_CONTEXT.md"
    context_file.write_text(shared_context, encoding="utf-8")
    logger.info(f"  Wrote {context_file}")

    # Step 3: Execute workers (semaphore-limited parallel)
    logger.info(f"\n[3/4] Executing workers ({'dual-model' if use_v2 else 'single-model'})...")
    all_files = []
    write_lock = threading.Lock()
    written = 0
    max_concurrent = 1 if use_v2 else 2  # Dual-model uses 2 API calls per worker, be conservative

    # Separate injected from API workers
    injected = [(idx, st) for idx, st in enumerate(subtasks) if st.get("injected")]
    api_workers = [(idx, st) for idx, st in enumerate(subtasks) if not st.get("injected")]

    # Write injected files first (no API calls)
    for idx, st in injected:
        logger.info(f"[worker-{idx}] Writing injected critical files: {st['files']}")
        for filename in st["files"]:
            content = CRITICAL_FILES.get(filename, "")
            if content:
                target = project_path / filename
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                with write_lock:
                    all_files.append({"path": filename, "content": content})
                    written += 1
                logger.info(f"  -> {filename}")

    # Execute API workers — Mark II runs sequentially to avoid rate limits
    logger.info(f"[sequential] Running {len(api_workers)} workers one at a time")
    results = []

    for idx, st in api_workers:
        if use_v2:
            files = execute_worker_v2(
                idx,
                st["generator"],
                st["reviewer"],
                st["description"],
                shared_context,
                st.get("files", []),
                rate_limiter,
            )
        else:
            files = execute_worker(
                idx,
                st["model"],
                st["description"],
                shared_context,
                st.get("files", []),
                rate_limiter,
            )

        if files:
            for f in files:
                path = f.get("path", "")
                content = f.get("content", "")
                if path and content:
                    target = project_path / path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(content, encoding="utf-8")
                    with write_lock:
                        all_files.append(f)
                        written += 1
                    logger.info(f"  -> {path}")
        results.append((idx, len(files) if files else 0))

    logger.info(f"[parallel] All {len(results)} workers completed")

    # Step 4: Repair phase — detect missing files + fix type mismatches
    logger.info(f"\n[4/5] Repair phase...")
    repaired = repair_phase(project_path, rate_limiter, subtasks, shared_context)
    if repaired:
        written += repaired
        logger.info(f"[repair] Fixed {repaired} files")
    else:
        logger.info(f"[repair] No issues found or repair skipped")

    # Step 5: Summary (files already written incrementally)
    logger.info(f"\n[5/5] Summary...")

    logger.info(f"\n{'='*60}")
    logger.info(f"DONE: {written} files written")
    logger.info(f"{'='*60}")

    # Save summary
    summary = {
        "pipeline": pipeline_name,
        "goal": goal,
        "timestamp": timestamp,
        "subtasks_planned": len(subtasks),
        "files_written": written,
        "log_file": str(log_file),
    }
    with open(project_path / "orchestration_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    return all_files


# ── CLI ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    use_v2 = "--v1" not in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if len(args) < 2:
        print("Usage: python -m autobots.orchestrator 'Build a counter app' D:\\projects\\counter [--v1]")
        print("  Mark II (default): dual-model gen+review per subtask")
        print("  --v1: use Mark I single-model (faster, fewer API calls)")
        sys.exit(1)

    goal = args[0]
    output = args[1]
    orchestrate(goal, output, use_v2=use_v2)
