"""build_project.py — Combined pipeline: generate → validate → fix → done.

Usage:
    python build_project.py "Build a tic-tac-toe game" D:\projects\tic-tac-toe
    python build_project.py "Build a todo app" D:\projects\todo --fix "Add dark mode"
"""

import argparse, json, os, re, socket, subprocess, sys, time
from pathlib import Path
from openai import OpenAI

API_KEY = os.environ.get("NVIDIA_API_KEY")
if not API_KEY:
    raise SystemExit("Set NVIDIA_API_KEY env var first")
BASE_URL = "https://integrate.api.nvidia.com/v1"
MODEL = "meta/llama-3.3-70b-instruct"
DEV_PORT = 5180
MAX_FIX_ATTEMPTS = 3

GEN_PROMPT = """You are a senior full-stack developer. Build what the user asks for.

CRITICAL RULES:
- Return complete, runnable files as JSON
- "content" field MUST be a string with the full file content
- Use \\n for newlines inside content strings
- Escape quotes inside content with \\". Do NOT use single quotes for JS/JSX.
- Return ONLY the JSON object, no explanation text

FILE LOCATION RULES:
- root "" (empty): index.html, package.json, tsconfig.json, vite.config.ts, .gitignore
- root "src": App.tsx, App.css, main.tsx, and all component files
- root "tests": test files
- index.html MUST reference src/main.tsx, not main.tsx

Return format:
{"files":[{"root":"","path":"filename.ext","content":"full file content here"}]}

root "" = project root directory
root "src" = src/ directory"""

UPDATE_PROMPT = """You are a senior full-stack developer. Modify an existing project.

RULES:
- Return complete, runnable files as JSON
- "content" field MUST be a string with the full file content
- Use \\n for newlines inside content strings
- Escape quotes inside content with \\". Do NOT use single quotes for JS/JSX.
- Return ONLY the JSON object, no explanation text
- Return ONLY files that need to change. Do NOT return unchanged files.
- Return the COMPLETE file, not a diff.

Return format:
{"files":[{"root":"","path":"filename.ext","content":"full file content here"}],"message":"optional explanation"}"""

FIX_PROMPT = """You are a senior full-stack developer. A project has build/type errors.

RULES:
- Return complete, runnable files as JSON
- "content" field MUST be a string with the full file content
- Use \\n for newlines inside content strings
- Escape quotes inside content with \\". Do NOT use single quotes for JS/JSX.
- Return ONLY the JSON object, no explanation text
- Fix ONLY the files related to the error.

Return format:
{"files":[{"root":"","path":"filename.ext","content":"full file content here"}]}"""

SKIP_DIRS = {".git", "node_modules", ".autobots-state", "context", "tests", "__pycache__"}

SKILLS_DIR = Path(__file__).parent.parent / "autobots" / "skills"

# Files the model commonly generates with bad tsconfig settings
TSCONFIG_FIXES = {
    "compilerOptions.skipLibCheck": True,
}


# ── Helpers ──────────────────────────────────────────────────────────────

def log(msg, indent=0):
    print(f"{'  ' * indent}{msg}", flush=True)


def load_skill(name):
    """Load a skill file and return its content as a string."""
    skill_file = SKILLS_DIR / f"{name}.md"
    if not skill_file.exists():
        return ""
    try:
        return skill_file.read_text(encoding="utf-8")
    except Exception:
        return ""


def kill_orphans():
    subprocess.run("taskkill /F /IM node.exe /T >nul 2>&1", shell=True)
    time.sleep(1)


def run_cmd(cmd, cwd, timeout=60):
    try:
        r = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, shell=True,
            env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
        )
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timed out"
    except Exception as e:
        return -1, "", str(e)


def wait_port(port, timeout):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect(("127.0.0.1", port))
            s.close()
            return True
        except (ConnectionRefusedError, OSError):
            pass
        time.sleep(2)
    return False


def call_model(system, user):
    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
    parts = []
    for chunk in client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.3, max_tokens=8192, stream=True,
        stream_options={"include_usage": True},
    ):
        if chunk.choices and chunk.choices[0].delta:
            c = getattr(chunk.choices[0].delta, "content", None) or ""
            if c:
                parts.append(c)
    return "".join(parts)


def parse_json(raw):
    candidate = raw.strip()
    fenced = re.search(r"```(?:json)?\s*\n(.*?)\n```", candidate, re.DOTALL)
    if fenced:
        candidate = fenced.group(1).strip()
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start != -1 and end != -1:
        candidate = candidate[start:end + 1]
    candidate = candidate.replace("\\\n", "\\n")
    return json.loads(candidate, strict=False)


def write_files(project_dir, files):
    written = []
    for f in files:
        root = f.get("root", "").strip()
        path = f.get("path", "").strip()
        content = f.get("content", "")
        if not path:
            continue
        target = (project_dir / root / path) if root else (project_dir / path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        written.append(str(target.relative_to(project_dir)))
    return written


def fix_project_issues(project_dir):
    """Fix common issues in generated projects."""
    # Ensure tsconfig has correct settings for Vite + React
    tsconfig = project_dir / "tsconfig.json"
    if tsconfig.exists():
        try:
            tc = json.loads(tsconfig.read_text(encoding="utf-8"))
            co = tc.setdefault("compilerOptions", {})
            changed = False
            if not co.get("skipLibCheck"):
                co["skipLibCheck"] = True
                changed = True
            if not co.get("allowSyntheticDefaultImports"):
                co["allowSyntheticDefaultImports"] = True
                changed = True
            if not co.get("esModuleInterop"):
                co["esModuleInterop"] = True
                changed = True
            if co.get("rootDir") == "src":
                del co["rootDir"]
                changed = True
            if changed:
                tsconfig.write_text(json.dumps(tc, indent=2), encoding="utf-8")
                log("Fixed tsconfig.json", 2)
        except Exception:
            pass

    # Ensure critical devDependencies are present
    pkg = project_dir / "package.json"
    if pkg.exists():
        try:
            p = json.loads(pkg.read_text(encoding="utf-8"))
            devdeps = p.setdefault("devDependencies", {})
            required_dev = {
                "@vitejs/plugin-react": "^2.1.0",
                "typescript": "^4.8.4",
                "vite": "^3.2.3",
            }
            changed = False
            for dep, ver in required_dev.items():
                if dep not in devdeps:
                    devdeps[dep] = ver
                    changed = True
                    log(f"Added missing devDep: {dep}", 2)
            if changed:
                pkg.write_text(json.dumps(p, indent=2), encoding="utf-8")
        except Exception:
            pass


def scan_project(project_dir):
    files = []
    for f in sorted(project_dir.rglob("*")):
        if not f.is_file():
            continue
        rel = str(f.relative_to(project_dir))
        parts = Path(rel).parts
        if any(p in SKIP_DIRS for p in parts):
            continue
        try:
            content = f.read_text(encoding="utf-8")
            files.append({"path": rel, "content": content})
        except Exception:
            files.append({"path": rel, "content": "<binary>"})
    return files


# ── Validation ───────────────────────────────────────────────────────────

def validate(project_dir):
    errors = []

    code, out, err = run_cmd(["npm", "install"], project_dir, timeout=300)
    if code != 0:
        errors.append(f"INSTALL FAILED:\n{(err or out)[-500:]}")
        return False, errors

    tsc = project_dir / "node_modules" / ".bin" / "tsc"
    if not tsc.exists():
        tsc = project_dir / "node_modules" / ".bin" / "tsc.cmd"
    if tsc.exists():
        code, out, err = run_cmd([str(tsc), "--noEmit"], project_dir, timeout=30)
        if code != 0:
            ts = [l for l in (out + err).splitlines() if "error TS" in l]
            errors.append("TYPE CHECK FAILED:\n" + "\n".join(ts[:20]))
            return False, errors

    code, out, err = run_cmd(["npm", "run", "build"], project_dir, timeout=60)
    if code != 0:
        errors.append(f"BUILD FAILED:\n{(err or out)[-1000:]}")
        return False, errors

    kill_orphans()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", DEV_PORT))
    except OSError:
        errors.append(f"Port {DEV_PORT} in use")
        return False, errors
    finally:
        sock.close()

    proc = subprocess.Popen(
        ["npm", "run", "dev", "--", "--port", str(DEV_PORT), "--host", "127.0.0.1"],
        cwd=project_dir, shell=True,
        env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
    )
    if not wait_port(DEV_PORT, 20):
        errors.append("Dev server did not start")
        proc.kill()
        return False, errors

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()

    return True, []


# ── Pipeline ─────────────────────────────────────────────────────────────

def init_git(project_dir):
    subprocess.run(["git", "init"], cwd=project_dir, capture_output=True, shell=True)
    subprocess.run(["git", "add", "."], cwd=project_dir, capture_output=True, shell=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial generation by Autobots"],
        cwd=project_dir, capture_output=True, shell=True,
    )


def generate(project_dir, goal):
    log(f"Generating project from goal: {goal}")
    frontend_skill = load_skill("frontend-developer")
    backend_skill = load_skill("backend-engineer")
    skill_context = ""
    if frontend_skill:
        skill_context += f"\n\n## Frontend Engineering Skill\n{frontend_skill[:3000]}"
    if backend_skill:
        skill_context += f"\n\n## Backend Engineering Skill\n{backend_skill[:3000]}"
    enhanced_prompt = GEN_PROMPT + skill_context
    raw = call_model(enhanced_prompt, goal)
    log(f"Model returned {len(raw)} chars", 1)
    payload = parse_json(raw)
    files = payload.get("files", [])
    written = write_files(project_dir, files)
    log(f"Wrote {len(written)} files", 1)
    for w in written:
        log(w, 2)
    return written


def fix_loop(project_dir):
    log("Running validation...")
    for attempt in range(1, MAX_FIX_ATTEMPTS + 1):
        passed, errors = validate(project_dir)
        if passed:
            log("Validation PASSED", 1)
            return True
        log(f"Attempt {attempt}: {len(errors)} error(s)", 1)
        for e in errors:
            log(e[:200], 2)

        if attempt == MAX_FIX_ATTEMPTS:
            log("Max fix attempts reached", 1)
            return False

        log(f"Asking model to fix (attempt {attempt})...", 1)
        files = scan_project(project_dir)
        existing = "\n".join(f"--- {f['path']} ---\n{f['content'][:2000]}" for f in files)
        error_text = "\n\n".join(errors)
        review_skill = load_skill("code-reviewer")
        skill_context = f"\n\n## Code Review Skill\n{review_skill[:2000]}" if review_skill else ""
        enhanced_fix_prompt = FIX_PROMPT + skill_context
        user_msg = f"Errors:\n{error_text}\n\nEXISTING FILES:\n{existing}\n\nFix the errors."

        raw = call_model(enhanced_fix_prompt, user_msg)
        try:
            payload = parse_json(raw)
            fix_files = payload.get("files", [])
        except Exception as e:
            log(f"Parse error: {e}", 2)
            return False

        if not fix_files:
            log("No fix files returned", 2)
            return False

        written = write_files(project_dir, fix_files)
        log(f"Fixed {len(written)} files", 2)
        fix_project_issues(project_dir)

        # Re-install deps in case package.json changed
        log("Re-installing dependencies...", 2)
        run_cmd(["npm", "install"], project_dir, timeout=300)

    return False


def apply_update(project_dir, instruction):
    log(f"Applying update: {instruction}")
    files = scan_project(project_dir)
    existing = "\n".join(f"--- {f['path']} ---\n{f['content'][:2000]}" for f in files)
    fullstack_skill = load_skill("fullstack-engineer")
    skill_context = f"\n\n## Fullstack Engineering Skill\n{fullstack_skill[:2000]}" if fullstack_skill else ""
    enhanced_update_prompt = UPDATE_PROMPT + skill_context
    user_msg = f"Current project:\n{existing}\n\nUser instruction: {instruction}\n\nReturn ONLY files that need to change."

    raw = call_model(enhanced_update_prompt, user_msg)
    log(f"Model returned {len(raw)} chars", 1)

    try:
        payload = parse_json(raw)
        changed = payload.get("files", [])
        msg = payload.get("message", "")
    except Exception as e:
        log(f"Parse error: {e}", 1)
        return False

    if msg:
        log(f"Message: {msg}", 1)

    if not changed:
        log("No changes needed", 1)
        return True

    written = write_files(project_dir, changed)
    log(f"Wrote {len(written)} files", 1)
    return True


def main():
    parser = argparse.ArgumentParser(description="Build a project from a goal")
    parser.add_argument("goal", help="What to build")
    parser.add_argument("output", help="Output directory")
    parser.add_argument("--fix", help="Optional: incremental instruction after build")
    args = parser.parse_args()

    project_dir = Path(args.output)
    project_dir.mkdir(parents=True, exist_ok=True)

    log(f"Output: {project_dir}")
    log(f"Goal: {args.goal}")
    log("")

    # Step 1: Generate
    log("=" * 50)
    log("PHASE 1: Generate")
    log("=" * 50)
    generate(project_dir, args.goal)

    log("Fixing common project issues...", 1)
    fix_project_issues(project_dir)

    # Step 2: Validate + Fix loop
    log("")
    log("=" * 50)
    log("PHASE 2: Validate + Fix")
    log("=" * 50)
    if not fix_loop(project_dir):
        log("FAILED after fix attempts")
        return 1

    # Step 3: Optional incremental update
    if args.fix:
        log("")
        log("=" * 50)
        log(f"PHASE 3: Incremental — {args.fix}")
        log("=" * 50)
        if not apply_update(project_dir, args.fix):
            log("Update FAILED")
            return 1
        log("")
        log("Re-validating after update...")
        if not fix_loop(project_dir):
            log("FAILED after update")
            return 1

    # Step 4: Init git
    log("")
    log("=" * 50)
    log("PHASE 4: Git init")
    log("=" * 50)
    init_git(project_dir)
    log("Git repo initialized", 1)

    log("")
    log("=" * 50)
    log("BUILD COMPLETE")
    log("=" * 50)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
