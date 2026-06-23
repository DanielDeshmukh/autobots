"""Phase 4: Validation - run the project and check it works."""

import subprocess, sys, time, os, socket
from pathlib import Path

PROJECT = Path(r"D:\Vs Code\VS code\tic-tac-toe")
TIMEOUT = 30
DEV_PORT = 5180


def kill_orphans():
    subprocess.run("taskkill /F /IM node.exe /T >nul 2>&1", shell=True)
    time.sleep(1)


def detect_project_type(project_dir: Path) -> dict:
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
    """Poll TCP socket until the port accepts connections."""
    deadline = time.time() + timeout
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect(("127.0.0.1", port))
            s.close()
            print(f"  [attempt {attempt}] Port {port} accepting connections")
            return True
        except (ConnectionRefusedError, OSError):
            print(f"  [attempt {attempt}] Port {port} not ready")
        time.sleep(2)
    return False


def check_typescript(project_dir: Path) -> list:
    tsc = project_dir / "node_modules" / ".bin" / "tsc"
    if not tsc.exists():
        tsc = project_dir / "node_modules" / ".bin" / "tsc.cmd"
    if not tsc.exists():
        return ["tsc not found (node_modules may not be installed)"]
    code, out, err = run_command([str(tsc), "--noEmit"], project_dir, timeout=30)
    if code != 0:
        return [line for line in (out + err).splitlines() if "error TS" in line]
    return []


def main():
    print(f"Project: {PROJECT}")
    print()

    config = detect_project_type(PROJECT)
    print(f"Project type: {config['type']}")

    if config["type"] == "unknown":
        print("Cannot detect project type.")
        return 1

    # Clean slate
    print()
    print("=" * 50)
    print("CLEANUP")
    print("=" * 50)
    kill_orphans()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", DEV_PORT))
        print(f"Port {DEV_PORT} is free")
    except OSError:
        print(f"Port {DEV_PORT} still in use")
        return 1
    finally:
        sock.close()

    # Step 1: Install
    print()
    print("=" * 50)
    print("STEP 1: Install dependencies")
    print("=" * 50)
    if config["install"]:
        print(f"Running: {' '.join(config['install'])}")
        code, out, err = run_command(config["install"], PROJECT, timeout=120)
        print(f"Exit code: {code}")
        if code != 0:
            if err:
                for line in err.strip().splitlines()[-5:]:
                    print(f"  {line}")
            print("FAILED")
            return 1
        print("OK")
    else:
        print("No install needed")

    # Step 2: Type check
    if config["type"] == "node" and (PROJECT / "tsconfig.json").exists():
        print()
        print("=" * 50)
        print("STEP 2: Type check")
        print("=" * 50)
        errors = check_typescript(PROJECT)
        if errors:
            print(f"Type errors: {len(errors)}")
            for e in errors[:10]:
                print(f"  {e}")
        else:
            print("OK")

    # Step 3: Build
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
            print("FAILED")
            return 1
        print("OK")

    # Step 4: Dev server
    print()
    print("=" * 50)
    print("STEP 4: Start dev server")
    print("=" * 50)
    if not config.get("dev"):
        print("No dev command")
        return 1

    dev_cmd = config["dev"] + ["--", "--port", str(DEV_PORT), "--host", "127.0.0.1"]
    print(f"Running: {' '.join(dev_cmd)}")
    proc = subprocess.Popen(
        dev_cmd,
        cwd=PROJECT,
        shell=True,
        env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
    )
    print(f"PID: {proc.pid}")

    print(f"Waiting for port {DEV_PORT} (timeout {TIMEOUT}s)...")
    if not wait_for_port(DEV_PORT, TIMEOUT):
        print("Server did NOT start")
        proc.kill()
        return 1

    print()
    print("Stopping server...")
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
