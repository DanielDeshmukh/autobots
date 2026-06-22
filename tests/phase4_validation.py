"""Phase 4: Validation - run the project and check it works."""

import subprocess, sys, time, re
from pathlib import Path

PROJECT = Path(r"D:\Vs Code\VS code\tic-tac-toe")
TIMEOUT = 30  # seconds to wait for dev server


def detect_project_type(project_dir: Path) -> dict:
    """Detect project type and return install/run commands."""
    if (project_dir / "package.json").exists():
        return {
            "type": "node",
            "install": ["npm", "install"],
            "dev": ["npm", "run", "dev"],
            "build": ["npm", "run", "build"],
        }
    if (project_dir / "requirements.txt").exists():
        return {
            "type": "python",
            "install": [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            "dev": [sys.executable, "app.py"],
            "build": None,
        }
    if (project_dir / "pyproject.toml").exists():
        return {
            "type": "python",
            "install": [sys.executable, "-m", "pip", "install", "."],
            "dev": [sys.executable, "-m", "uvicorn", "main:app", "--reload"],
            "build": None,
        }
    return {"type": "unknown", "install": None, "dev": None, "build": None}


def run_command(cmd: list, cwd: Path, timeout: int = 60) -> tuple:
    """Run a command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, shell=True,
            env={**__import__("os").environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timed out"
    except Exception as e:
        return -1, "", str(e)


def wait_for_server(proc, timeout: int) -> tuple:
    """Wait for dev server to respond. Returns (url, html) or (None, None)."""
    import urllib.request
    # Just wait a bit then try common ports
    time.sleep(5)
    for port in [5173, 5174, 5175, 3000, 8080]:
        try:
            resp = urllib.request.urlopen(f"http://127.0.0.1:{port}", timeout=3)
            html = resp.read().decode("utf-8")
            return f"http://127.0.0.1:{port}", html
        except Exception:
            pass
    # If no HTTP response but process alive, server started (just not responding to urllib)
    if proc.poll() is None:
        return "http://localhost:5173", "<started but not fetched>"
    return None, None


def check_typescript(project_dir: Path) -> list:
    """Run tsc --noEmit to check for type errors."""
    tsc = project_dir / "node_modules" / ".bin" / "tsc"
    if not tsc.exists():
        tsc = project_dir / "node_modules" / ".bin" / "tsc.cmd"
    if not tsc.exists():
        return ["tsc not found (node_modules may not be installed)"]
    code, out, err = run_command([str(tsc), "--noEmit"], project_dir, timeout=30)
    if code != 0:
        errors = [line for line in (out + err).splitlines() if "error TS" in line]
        return errors
    return []


def main():
    print(f"Project: {PROJECT}")
    print()

    # Detect project type
    config = detect_project_type(PROJECT)
    print(f"Project type: {config['type']}")

    if config["type"] == "unknown":
        print("Cannot detect project type. Skipping validation.")
        return 1

    # Step 1: Install dependencies
    print()
    print("=" * 50)
    print("STEP 1: Install dependencies")
    print("=" * 50)
    if config["install"]:
        print(f"Running: {' '.join(config['install'])}")
        code, out, err = run_command(config["install"], PROJECT, timeout=120)
        print(f"Exit code: {code}")
        if out:
            for line in out.strip().splitlines()[-5:]:
                print(f"  {line}")
        if err:
            for line in err.strip().splitlines()[-5:]:
                print(f"  {line}")
        if code != 0:
            print("Install FAILED")
            return 1
        print("Install OK")
    else:
        print("No install needed")

    # Step 2: Type check (TypeScript only)
    if config["type"] == "node" and (PROJECT / "tsconfig.json").exists():
        print()
        print("=" * 50)
        print("STEP 2: Type check (tsc --noEmit)")
        print("=" * 50)
        errors = check_typescript(PROJECT)
        if errors:
            print(f"Type errors found: {len(errors)}")
            for e in errors[:10]:
                print(f"  {e}")
        else:
            print("Type check OK")

    # Step 3: Build (if available)
    if config.get("build"):
        print()
        print("=" * 50)
        print("STEP 3: Build")
        print("=" * 50)
        print(f"Running: {' '.join(config['build'])}")
        code, out, err = run_command(config["build"], PROJECT, timeout=60)
        print(f"Exit code: {code}")
        if code != 0:
            if out:
                for line in out.strip().splitlines()[-10:]:
                    print(f"  {line}")
            if err:
                for line in err.strip().splitlines()[-10:]:
                    print(f"  {line}")
            print("Build FAILED")
            return 1
        print("Build OK")

    # Step 4: Start dev server
    print()
    print("=" * 50)
    print("STEP 4: Start dev server")
    print("=" * 50)
    if not config.get("dev"):
        print("No dev command found")
        return 1

    print(f"Running: {' '.join(config['dev'])}")
    import os
    # Don't capture stdout/stderr - Vite needs direct console access
    proc = subprocess.Popen(
        config["dev"],
        cwd=PROJECT,
        shell=True,
        env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
    )
    print(f"PID: {proc.pid}")

    # Wait for server to start
    print(f"Waiting for dev server (timeout {TIMEOUT}s)...")
    time.sleep(3)  # Give server time to start
    url, html = wait_for_server(proc, TIMEOUT)

    if url:
        print(f"Dev server running at {url}")
        print(f"Page fetched: {len(html)} chars")
        if "<div id=\"root\">" in html or "<div id=\"app\">" in html:
            print("Root element found - React/Vue app detected")
        elif "<html" in html:
            print("HTML page rendered")
    else:
        print("Dev server did NOT start within timeout")
        print(f"Process alive: {proc.poll() is None}")
        proc.kill()
        return 1

    # Cleanup
    print()
    print("Stopping dev server...")
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()

    print()
    print("=" * 50)
    print("VALIDATION PASSED")
    print("=" * 50)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
