"""Generate tic-tac-toe files directly to disk, no swarm."""

import json, os, re, sys
from pathlib import Path
from openai import OpenAI

API_KEY = os.environ.get("NVIDIA_API_KEY")
if not API_KEY:
    raise SystemExit("Set NVIDIA_API_KEY env var first")
BASE_URL = "https://integrate.api.nvidia.com/v1"
MODEL = "meta/llama-3.3-70b-instruct"
PROJECT = Path(r"D:\Vs Code\VS code\tic-tac-toe")

PROMPT = """You are a senior full-stack developer. Build what the user asks for.

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
    print(f"Output: {PROJECT}")
    print()

    # Generate
    print("Generating...")
    raw = call_model(PROMPT, goal)
    print(f"Response: {len(raw)} chars")

    payload = parse_json(raw)
    files = payload.get("files", [])
    print(f"Files: {len(files)}")

    written = write_files(PROJECT, files)
    print(f"\nWritten {len(written)} files:")
    for w in written:
        print(f"  {w}")

    # Show required files check
    print()
    required = ["package.json", "index.html", "vite.config.ts", "tsconfig.json", "src/App.tsx", "src/main.tsx"]
    for name in required:
        exists = (PROJECT / name).exists()
        print(f"  [{'OK' if exists else 'MISSING'}] {name}")

    print("\nDone.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
