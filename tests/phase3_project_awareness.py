"""Phase 3: Project awareness - scan existing files, generate only what's missing."""

import json, os, re, sys
from pathlib import Path
from openai import OpenAI

API_KEY = os.environ.get("NVIDIA_API_KEY")
if not API_KEY:
    raise SystemExit("Set NVIDIA_API_KEY env var first")
BASE_URL = "https://integrate.api.nvidia.com/v1"
MODEL = "meta/llama-3.3-70b-instruct"
PROJECT = Path(r"D:\Vs Code\VS code\tic-tac-toe")

GENERATOR_PROMPT = """You are a senior full-stack developer. Build what the user asks for.

CRITICAL RULES:
- Return complete, runnable files as JSON
- "content" field MUST be a string with the full file content
- Use \\n for newlines inside content strings
- Escape quotes inside content with \\". Do NOT use single quotes for JS/JSX.
- Return ONLY the JSON object, no explanation text

The user will tell you what files already exist in the project.
- Do NOT regenerate files that already exist
- Only generate MISSING files
- If all files exist, return {"files": [], "message": "All files already present"}

FILE LOCATION RULES:
- root "" (empty): index.html, package.json, tsconfig.json, vite.config.ts, .gitignore
- root "src": App.tsx, App.css, main.tsx, and all component files
- root "tests": test files

Return format:
{"files":[{"root":"","path":"filename.ext","content":"full file content here"}]}

root "" = project root directory
root "src" = src/ directory"""


SKIP_DIRS = {".git", "node_modules", ".autobots-state", "context", "tests"}

def scan_project(project_dir: Path) -> dict:
    """Scan project and return structured info about existing files."""
    existing = []
    for f in sorted(project_dir.rglob("*")):
        if not f.is_file():
            continue
        rel = str(f.relative_to(project_dir))
        # Skip hidden dirs, node_modules, context, tests
        parts = Path(rel).parts
        if any(p.startswith(".") or p in SKIP_DIRS for p in parts):
            continue
        try:
            content = f.read_text(encoding="utf-8")
            existing.append({"path": rel, "content": content})
        except Exception:
            existing.append({"path": rel, "content": "<binary or unreadable>"})
    return {
        "root": str(project_dir),
        "files": existing,
        "file_count": len(existing),
        "has_package_json": (project_dir / "package.json").exists(),
        "has_index_html": (project_dir / "index.html").exists(),
        "has_vite_config": (project_dir / "vite.config.ts").exists(),
        "has_tsconfig": (project_dir / "tsconfig.json").exists(),
        "has_src_main": (project_dir / "src" / "main.tsx").exists(),
        "has_src_app": (project_dir / "src" / "App.tsx").exists(),
    }


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


def main():
    goal = sys.argv[1] if len(sys.argv) > 1 else "Build a tic-tac-toe game with React, Vite, and TypeScript"
    print(f"Goal: {goal}")
    print(f"Project: {PROJECT}")
    print()

    # Step 1: Scan existing files
    print("=" * 50)
    print("STEP 1: Scan existing files")
    print("=" * 50)
    scan = scan_project(PROJECT)
    print(f"Found {len(scan['files'])} source files:")
    for f in scan["files"]:
        print(f"  {f['path']} ({len(f['content'])} chars)")

    # Step 2: Generate missing files
    print()
    print("=" * 50)
    print("STEP 2: Generate missing files")
    print("=" * 50)

    # Build user message with scan info — include file contents so model knows exactly what exists
    existing_summary = "\n".join(f"--- {f['path']} ---\n{f['content']}" for f in scan["files"])
    user_msg = f"""Goal: {goal}

EXISTING FILES (DO NOT REGENERATE THESE):
{existing_summary}

Generate ONLY files that are MISSING from the project above.
If all files needed for the goal already exist, return {{"files": [], "message": "All files already present"}}."""

    raw = call_model(GENERATOR_PROMPT, user_msg)
    print(f"Response: {len(raw)} chars")

    payload = parse_json(raw)
    files = payload.get("files", [])
    message = payload.get("message", "")
    print(f"Files to generate: {len(files)}")
    if message:
        print(f"Message: {message}")

    if files:
        written = write_files(PROJECT, files)
        print(f"\nWritten {len(written)} new files:")
        for w in written:
            print(f"  {w}")
    else:
        print("\nNo new files needed!")

    # Step 3: Verify
    print()
    print("=" * 50)
    print("STEP 3: Verify project state")
    print("=" * 50)
    final_scan = scan_project(PROJECT)
    print(f"Total source files: {len(final_scan['files'])}")
    required = ["package.json", "index.html", "vite.config.ts", "tsconfig.json", "src/App.tsx", "src/main.tsx"]
    for name in required:
        exists = (PROJECT / name).exists()
        print(f"  [{'OK' if exists else 'MISSING'}] {name}")

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
