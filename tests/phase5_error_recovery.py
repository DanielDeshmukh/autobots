"""Phase 5: Error Recovery - feed validation errors back to model, get fixes, retry."""

import json, os, re, sys, socket, subprocess, time
from pathlib import Path
from openai import OpenAI

API_KEY = os.environ.get("NVIDIA_API_KEY")
if not API_KEY:
    raise SystemExit("Set NVIDIA_API_KEY env var first")
BASE_URL = "https://integrate.api.nvidia.com/v1"
MODEL = "meta/llama-3.3-70b-instruct"
PROJECT = Path(r"D:\Vs Code\VS code\tic-tac-toe")
MAX_RETRIES = 3
DEV_PORT = 5180

FIX_PROMPT = """You are a senior full-stack developer. A project has build/type/runtime errors.

RULES:
- Return complete, runnable files as JSON
- "content" field MUST be a string with the full file content
- Use \\n for newlines inside content strings
- Escape quotes inside content with \\". Do NOT use single quotes for JS/JSX.
- Return ONLY the JSON object, no explanation text
- Fix ONLY the files related to the error. Do NOT rewrite unrelated files.
- If a file is not mentioned in the error, include it unchanged in your response.

Return format:
{"files":[{"root":"","path":"filename.ext","content":"full file content here"}]}

root "" = project root directory
root "src" = src/ directory"""


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
    """Run validation steps. Returns (passed: bool, errors: list[str])."""
    errors = []

    # Install
    code, out, err = run_command(["npm", "install"], project_dir, timeout=120)
    if code != 0:
        errors.append(f"INSTALL FAILED:\n{(err or out)[-500:]}")
        return False, errors

    # Type check
    tsc = project_dir / "node_modules" / ".bin" / "tsc"
    if not tsc.exists():
        tsc = project_dir / "node_modules" / ".bin" / "tsc.cmd"
    if tsc.exists():
        code, out, err = run_command([str(tsc), "--noEmit"], project_dir, timeout=30)
        if code != 0:
            ts_errors = [line for line in (out + err).splitlines() if "error TS" in line]
            errors.append(f"TYPE CHECK FAILED:\n" + "\n".join(ts_errors[:20]))
            return False, errors

    # Build
    code, out, err = run_command(["npm", "run", "build"], project_dir, timeout=60)
    if code != 0:
        errors.append(f"BUILD FAILED:\n{(err or out)[-1000:]}")
        return False, errors

    # Dev server
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


def main():
    print(f"Project: {PROJECT}")
    print(f"Model: {MODEL}")
    print(f"Max retries: {MAX_RETRIES}")
    print()

    for attempt in range(1, MAX_RETRIES + 1):
        print("=" * 50)
        print(f"ATTEMPT {attempt}/{MAX_RETRIES}")
        print("=" * 50)

        passed, errors = run_validation(PROJECT)

        if passed:
            print()
            print("=" * 50)
            print("VALIDATION PASSED")
            print("=" * 50)
            return 0

        # Log errors
        error_text = "\n\n".join(errors)
        print(f"Validation failed with {len(errors)} error(s):")
        for e in errors:
            print(f"  {e[:200]}")

        if attempt == MAX_RETRIES:
            print()
            print("MAX RETRIES REACHED - giving up")
            return 1

        # Ask model to fix
        print()
        print("=" * 50)
        print(f"ASKING MODEL TO FIX (attempt {attempt})")
        print("=" * 50)

        files = scan_project(PROJECT)
        existing = "\n".join(f"--- {f['path']} ---\n{f['content'][:2000]}" for f in files)

        user_msg = f"""The project has the following errors:

{error_text}

EXISTING FILES:
{existing}

Fix the errors by returning corrected files. Return ONLY the JSON object."""

        raw = call_model(FIX_PROMPT, user_msg)
        print(f"Model response: {len(raw)} chars")

        try:
            payload = parse_json(raw)
            fix_files = payload.get("files", [])
            print(f"Files returned: {len(fix_files)}")
        except Exception as e:
            print(f"Failed to parse model response: {e}")
            print(f"Raw response (first 500 chars): {raw[:500]}")
            return 1

        if not fix_files:
            print("Model returned no files - nothing to fix")
            return 1

        written = write_files(PROJECT, fix_files)
        print(f"Written {len(written)} files:")
        for w in written:
            print(f"  {w}")

        print()
        print("Re-running validation...")
        print()

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
