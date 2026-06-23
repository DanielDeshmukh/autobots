"""Phase 6: Incremental updates - modify existing project without regenerating everything."""

import json, os, re, sys, socket, subprocess, time
from pathlib import Path
from openai import OpenAI

API_KEY = os.environ.get("NVIDIA_API_KEY")
if not API_KEY:
    raise SystemExit("Set NVIDIA_API_KEY env var first")
BASE_URL = "https://integrate.api.nvidia.com/v1"
MODEL = "meta/llama-3.3-70b-instruct"
PROJECT = Path(r"D:\Vs Code\VS code\tic-tac-toe")
MAX_FIX_RETRIES = 2
DEV_PORT = 5180

UPDATE_PROMPT = """You are a senior full-stack developer. The user wants to modify an existing project.

RULES:
- Return complete, runnable files as JSON
- "content" field MUST be a string with the full file content
- Use \\n for newlines inside content strings
- Escape quotes inside content with \\". Do NOT use single quotes for JS/JSX.
- Return ONLY the JSON object, no explanation text
- Return ONLY the files that need to change. Do NOT return unchanged files.
- If a file needs changes, return the COMPLETE file, not a diff.
- If no files need to change, return {"files": [], "message": "No changes needed"}

FILE LOCATION RULES:
- root "" (empty): index.html, package.json, etc. in project root
- root "src": component and source files

Return format:
{"files":[{"root":"","path":"filename.ext","content":"full file content here"}],"message":"optional explanation"}"""

FIX_PROMPT = """You are a senior full-stack developer. A project has build/type errors after a modification.

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


def kill_orphans():
    subprocess.run("taskkill /F /IM node.exe /T >nul 2>&1", shell=True)
    time.sleep(1)


def run_command(cmd: list, cwd: Path, timeout: int = 60) -> tuple:
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, shell=True,
            env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timed out"
    except Exception as e:
        return -1, "", str(e)


def wait_for_port(port: int, timeout: int) -> bool:
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


def scan_project(project_dir: Path) -> list:
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
            files.append({"path": rel, "content": "<binary or unreadable>"})
    return files


def run_validation(project_dir: Path) -> tuple:
    errors = []

    code, out, err = run_command(["npm", "install"], project_dir, timeout=120)
    if code != 0:
        errors.append(f"INSTALL FAILED:\n{(err or out)[-500:]}")
        return False, errors

    tsc = project_dir / "node_modules" / ".bin" / "tsc"
    if not tsc.exists():
        tsc = project_dir / "node_modules" / ".bin" / "tsc.cmd"
    if tsc.exists():
        code, out, err = run_command([str(tsc), "--noEmit"], project_dir, timeout=30)
        if code != 0:
            ts_errors = [line for line in (out + err).splitlines() if "error TS" in line]
            errors.append(f"TYPE CHECK FAILED:\n" + "\n".join(ts_errors[:20]))
            return False, errors

    code, out, err = run_command(["npm", "run", "build"], project_dir, timeout=60)
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

    dev_cmd = ["npm", "run", "dev", "--", "--port", str(DEV_PORT), "--host", "127.0.0.1"]
    proc = subprocess.Popen(
        dev_cmd, cwd=project_dir, shell=True,
        env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
    )
    if not wait_for_port(DEV_PORT, 20):
        errors.append("Dev server did not start")
        proc.kill()
        return False, errors

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()

    return True, []


def try_fix(project_dir: Path, error_text: str) -> bool:
    """Send errors to model, get fixes, write them. Returns True if fix applied."""
    files = scan_project(project_dir)
    existing = "\n".join(f"--- {f['path']} ---\n{f['content'][:2000]}" for f in files)

    user_msg = f"""The project has errors after a modification:

{error_text}

EXISTING FILES:
{existing}

Fix the errors. Return ONLY the JSON object."""

    raw = call_model(FIX_PROMPT, user_msg)
    print(f"  Fix response: {len(raw)} chars")

    try:
        payload = parse_json(raw)
        fix_files = payload.get("files", [])
    except Exception as e:
        print(f"  Failed to parse fix response: {e}")
        return False

    if not fix_files:
        print("  Model returned no fix files")
        return False

    written = write_files(project_dir, fix_files)
    print(f"  Written {len(written)} fix files: {written}")
    return True


def main():
    instruction = sys.argv[1] if len(sys.argv) > 1 else "Add a score counter that shows at the top of the game"
    print(f"Project: {PROJECT}")
    print(f"Instruction: {instruction}")
    print(f"Model: {MODEL}")
    print()

    # Step 1: Scan existing project
    print("=" * 50)
    print("STEP 1: Scan existing project")
    print("=" * 50)
    files = scan_project(PROJECT)
    print(f"Found {len(files)} source files")

    # Step 2: Ask model what to change
    print()
    print("=" * 50)
    print("STEP 2: Ask model to modify project")
    print("=" * 50)

    existing = "\n".join(f"--- {f['path']} ---\n{f['content'][:2000]}" for f in files)
    user_msg = f"""Current project files:
{existing}

User instruction: {instruction}

Return ONLY the files that need to change to implement this."""

    raw = call_model(UPDATE_PROMPT, user_msg)
    print(f"Response: {len(raw)} chars")

    try:
        payload = parse_json(raw)
        changed_files = payload.get("files", [])
        message = payload.get("message", "")
    except Exception as e:
        print(f"Failed to parse response: {e}")
        print(f"Raw (first 500): {raw[:500]}")
        return 1

    print(f"Files to modify: {len(changed_files)}")
    if message:
        print(f"Message: {message}")

    if not changed_files:
        print("No changes needed")
        return 0

    written = write_files(PROJECT, changed_files)
    print(f"Written {len(written)} files:")
    for w in written:
        print(f"  {w}")

    # Step 3: Validate
    print()
    print("=" * 50)
    print("STEP 3: Validate")
    print("=" * 50)

    for fix_attempt in range(MAX_FIX_RETRIES + 1):
        passed, errors = run_validation(PROJECT)
        if passed:
            print()
            print("=" * 50)
            print("UPDATE SUCCEEDED")
            print("=" * 50)
            return 0

        if fix_attempt == MAX_FIX_RETRIES:
            print(f"Failed after {MAX_FIX_RETRIES} fix attempts")
            return 1

        error_text = "\n".join(errors)
        print(f"Validation failed: {error_text[:300]}")
        print(f"Attempting fix {fix_attempt + 1}/{MAX_FIX_RETRIES}...")

        if not try_fix(PROJECT, error_text):
            print("Could not apply fix")
            return 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
