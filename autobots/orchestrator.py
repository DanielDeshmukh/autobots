"""orchestrator.py — Multi-model swarm with shared context.

Each model builds 1-2 files. They share a context markdown so everyone
knows what's being built and how to integrate.

Flow:
1. Planner decomposes task → assigns models to subtasks
2. Shared context markdown is created
3. Workers execute in parallel, each generating 1-2 files
4. Merger combines all outputs

All API responses are logged to logs/ directory.
"""

import json, os, re, time, threading, logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from openai import OpenAI


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

logger = logging.getLogger("orchestrator")
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
- TypeScript where applicable

Return JSON: {{"files": [{{"path": "...", "content": "..."}}]}}"""


# ── JSON Parser ────────────────────────────────────────────────────────────

def parse_json_response(content, context=""):
    """Parse JSON from model response, handling common issues."""
    logger.debug(f"[json] Parsing response ({len(content)} chars) {context}")

    # Strip markdown code fences
    content = re.sub(r"```json\s*", "", content)
    content = re.sub(r"```\s*$", "", content)
    content = re.sub(r"```\s*", "", content)

    # Try to find JSON object
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if not match:
        logger.debug(f"[json] No JSON object found")
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
        # Fix unescaped literal newlines
        lambda s: s.replace('\n', '\\n'),
        # Fix unescaped carriage returns
        lambda s: s.replace('\r', ''),
        # Fix unescaped tabs
        lambda s: s.replace('\t', '\\t'),
        # Fix single quotes
        lambda s: s.replace("'", '"'),
    ]

    for fix in fixes:
        try:
            fixed = fix(raw)
            data = json.loads(fixed)
            logger.debug(f"[json] Fixed parse succeeded with: {fix.__name__}")
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

    logger.debug(f"[json] All parse attempts failed")
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

        # Retry logic for rate limits
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
                if "429" in str(e) and attempt < max_retries - 1:
                    logger.warning(f"[worker-{idx}] Rate limited, backing off (attempt {attempt + 1})")
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


# ── Orchestrator ───────────────────────────────────────────────────────────

def orchestrate(goal, project_dir):
    """Main orchestration flow."""
    project_path = Path(project_dir)
    project_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"\n{'='*60}")
    logger.info(f"ORCHESTRATING: {goal}")
    logger.info(f"{'='*60}")
    logger.info(f"Log file: {log_file}")

    rate_limiter = RateLimiter(max_per_minute=35, min_interval=2.0)

    # Step 1: Plan subtasks
    logger.info(f"\n[1/4] Planning subtasks...")
    subtasks = plan_subtasks(goal, rate_limiter)

    if not subtasks:
        logger.error("No subtasks planned. Aborting.")
        return []

    # Step 1.5: Ensure critical files are included
    subtasks = ensure_critical_files(project_path, subtasks)

    # Step 2: Build shared context
    logger.info(f"\n[2/4] Building shared context...")
    shared_context = build_shared_context(goal, subtasks)
    context_file = project_path / "SHARED_CONTEXT.md"
    context_file.write_text(shared_context, encoding="utf-8")
    logger.info(f"  Wrote {context_file}")

    # Step 3: Execute workers
    logger.info(f"\n[3/4] Executing workers...")
    all_files = []

    for idx in range(len(subtasks)):
        st = subtasks[idx]

        # Handle injected critical files (no API call needed)
        if st.get("injected"):
            logger.info(f"[worker-{idx}] Writing injected critical files: {st['files']}")
            for filename in st["files"]:
                content = CRITICAL_FILES.get(filename, "")
                if content:
                    all_files.append({"path": filename, "content": content})
            continue

        files = execute_worker(
            idx,
            st["model"],
            st["description"],
            shared_context,
            st.get("files", []),
            rate_limiter,
        )
        if files:
            all_files.extend(files)

        # Small delay between workers
        if idx < len(subtasks) - 1:
            time.sleep(1)

    # Step 4: Write all files
    logger.info(f"\n[4/4] Writing {len(all_files)} files...")
    written = 0
    for f in all_files:
        path = f.get("path", "")
        content = f.get("content", "")
        if path and content:
            target = project_path / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            logger.info(f"  -> {path}")
            written += 1

    logger.info(f"\n{'='*60}")
    logger.info(f"DONE: {written} files written")
    logger.info(f"{'='*60}")

    # Save summary
    summary = {
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
    if len(sys.argv) < 3:
        print("Usage: python orchestrator.py 'Build a counter app' D:\\projects\\counter")
        sys.exit(1)

    goal = sys.argv[1]
    output = sys.argv[2]
    orchestrate(goal, output)
