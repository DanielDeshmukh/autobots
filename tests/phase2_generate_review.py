"""
Phase 2: Generate -> Review -> Fix.
Two models, no swarm, no clusters.
"""

import json
import os
import re
import sys
import tempfile
from pathlib import Path

from openai import OpenAI

API_KEY = os.environ.get("NVIDIA_API_KEY")
if not API_KEY:
    raise SystemExit("Set NVIDIA_API_KEY env var first")
BASE_URL = "https://integrate.api.nvidia.com/v1"
GENERATOR_MODEL = "meta/llama-3.3-70b-instruct"
REVIEWER_MODEL = "meta/llama-3.3-70b-instruct"

GENERATOR_PROMPT = """You are a senior full-stack developer. Build what the user asks for.

CRITICAL RULES:
- Return complete, runnable files as JSON
- "content" field MUST be a string with the full file content
- Use \\n for newlines inside content strings
- Escape quotes inside content with \\"
- Return ONLY the JSON object, no explanation text

FILE LOCATION RULES:
- root "" (empty): index.html, package.json, tsconfig.json, vite.config.ts, .gitignore
- root "src": App.tsx, App.css, main.tsx, and all component files
- index.html MUST reference src/main.tsx, not main.tsx

Return format:
{"files":[{"root":"","path":"filename.ext","content":"full file content here"}]}

root "" = project root directory
root "src" = src/ directory"""

REVIEWER_PROMPT = """You are a code reviewer. Review the generated project files for issues.

Check for:
1. Missing files (index.html, package.json, tsconfig.json, vite.config.ts)
2. Incorrect file locations:
   - index.html, package.json, tsconfig.json, vite.config.ts MUST be at root ""
   - App.tsx, main.tsx, App.css, components MUST be at root "src"
3. index.html must reference /src/main.tsx (with src/ prefix)
4. main.tsx must import from ./App (not App.tsx)
5. Missing imports or dependencies
6. Broken code (syntax errors, wrong React usage)
7. Duplicate files (same file at root and in src/)

Return strict JSON:
{
  "issues": ["issue 1", "issue 2"],
  "fixes": [
    {"root": "", "path": "filename.ext", "content": "corrected content"}
  ]
}

If no issues, return {"issues": [], "fixes": []}
Only include files that need fixing in "fixes".


Here are the generated files to review:

"""


def call_model(model: str, system: str, user: str) -> str:
    """Call model with streaming."""
    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
    full_response = []
    for chunk in client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.3,
        max_tokens=8192,
        stream=True,
        stream_options={"include_usage": True},
    ):
        if chunk.choices and chunk.choices[0].delta:
            content = getattr(chunk.choices[0].delta, "content", None) or ""
            if content:
                full_response.append(content)
    return "".join(full_response)


def parse_json(raw: str) -> dict:
    """Parse JSON from model response."""
    candidate = raw.strip()
    fenced = re.search(r"```(?:json)?\s*\n(.*?)\n```", candidate, re.DOTALL)
    if fenced:
        candidate = fenced.group(1).strip()
    if not candidate.startswith("{"):
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end != -1:
            candidate = candidate[start:end + 1]
    # Fix common escape issues
    candidate = candidate.replace("\\\n", "\\n")  # literal backslash-newline -> \n
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError:
        # Try with strict=False to handle some edge cases
        payload = json.loads(candidate, strict=False)
    if "files" in payload:
        for f in payload["files"]:
            if not isinstance(f.get("content"), str):
                f["content"] = json.dumps(f["content"], indent=2)
    return payload


def write_files(project_dir: Path, files: list[dict]) -> list[str]:
    """Write files to project directory."""
    written = []
    for f in files:
        root = f.get("root", "").strip()
        path = f.get("path", "").strip()
        content = f.get("content", "")
        if not path:
            continue
        if root:
            target = project_dir / root / path
        else:
            target = project_dir / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        written.append(str(target.relative_to(project_dir)))
    return written


def files_to_text(project_dir: Path) -> str:
    """Convert project files to text for reviewer."""
    parts = []
    for f in sorted(project_dir.rglob("*")):
        if f.is_file() and ".autobots" not in str(f):
            rel = f.relative_to(project_dir)
            try:
                content = f.read_text(encoding="utf-8")
                parts.append(f"--- {rel} ---\n{content}")
            except Exception:
                pass
    return "\n\n".join(parts)


def main():
    goal = sys.argv[1] if len(sys.argv) > 1 else "Build a tic-tac-toe game with React, Vite, and TypeScript"

    print(f"Goal: {goal}")
    print()

    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        # Step 1: Generate
        print("=" * 50)
        print("STEP 1: Generate")
        print("=" * 50)
        raw = call_model(GENERATOR_MODEL, GENERATOR_PROMPT, goal)
        print(f"Response: {len(raw)} chars")

        payload = parse_json(raw)
        files = payload.get("files", [])
        print(f"Files: {len(files)}")

        written = write_files(project_dir, files)
        print(f"Written: {len(written)} files")
        for w in written:
            print(f"  {w}")

        # Step 2: Review
        print()
        print("=" * 50)
        print("STEP 2: Review")
        print("=" * 50)
        files_text = files_to_text(project_dir)
        review_raw = call_model(REVIEWER_MODEL, REVIEWER_PROMPT, REVIEWER_PROMPT + files_text)
        print(f"Review response: {len(review_raw)} chars")

        try:
            review = parse_json(review_raw)
        except Exception as e:
            print(f"Review parse error: {e}")
            review = {"issues": ["Failed to parse review"], "fixes": []}

        issues = review.get("issues", [])
        fixes = review.get("fixes", [])
        print(f"Issues found: {len(issues)}")
        for i, issue in enumerate(issues):
            print(f"  {i+1}. {issue}")
        print(f"Fixes: {len(fixes)}")

        # Step 3: Apply fixes
        if fixes:
            print()
            print("=" * 50)
            print("STEP 3: Apply Fixes")
            print("=" * 50)
            fix_written = write_files(project_dir, fixes)
            print(f"Applied {len(fix_written)} fixes")
            for w in fix_written:
                print(f"  {w}")

        # Final state
        print()
        print("=" * 50)
        print("FINAL PROJECT")
        print("=" * 50)
        for f in sorted(project_dir.rglob("*")):
            if f.is_file() and ".autobots" not in str(f):
                rel = f.relative_to(project_dir)
                size = f.stat().st_size
                print(f"  {rel} ({size} bytes)")

        # Check required files
        print()
        required = {
            "package.json": "root",
            "index.html": "root",
            "vite.config.ts": "root",
            "tsconfig.json": "root",
            "src/App.tsx": "src",
            "src/main.tsx": "src",
        }
        for name, loc in required.items():
            exists = (project_dir / name).exists()
            status = "OK" if exists else "MISSING"
            print(f"  [{status}] {name} (should be at {loc})")

    print()
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
