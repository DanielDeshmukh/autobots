"""
Phase 1: One model, one prompt, one file.
No swarm, no clusters, no skills. Just OpenAI SDK -> model -> JSON -> write files.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

from openai import OpenAI

API_KEY = os.getenv("NVIDIA_API_KEY", "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")
BASE_URL = "https://integrate.api.nvidia.com/v1"
MODEL = "meta/llama-3.3-70b-instruct"

SYSTEM_PROMPT = """You are a senior full-stack developer. Build what the user asks for.

CRITICAL RULES:
- Return complete, runnable files as JSON
- "content" field MUST be a string with the full file content
- Use \\n for newlines inside content strings
- Escape quotes inside content with \\"
- Include ALL config files the project needs
- Return ONLY the JSON object, no explanation text

Return format:
{"files":[{"root":"","path":"filename.ext","content":"full file content here"}]}

root "" = project root directory
root "src" = src/ directory
Only use roots that make sense for the project type."""


def call_model(user_prompt: str) -> str:
    """Call model with clean prompt, no skills, no coordination laws."""
    client = OpenAI(
        base_url=BASE_URL,
        api_key=API_KEY,
    )

    full_response = []
    for chunk in client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
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


def parse_response(raw: str) -> dict:
    """Parse JSON from model response."""
    import re
    candidate = raw.strip()
    # Try to find JSON block in markdown fences
    fenced = re.search(r"```(?:json)?\s*\n(.*?)\n```", candidate, re.DOTALL)
    if fenced:
        candidate = fenced.group(1).strip()
    # If still not JSON, find first { and last }
    if not candidate.startswith("{"):
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end != -1:
            candidate = candidate[start:end + 1]
    payload = json.loads(candidate)
    # Fix: if content is an object/list instead of string, convert it
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


def main():
    goal = sys.argv[1] if len(sys.argv) > 1 else "Build a tic-tac-toe game with React, Vite, and TypeScript"

    print(f"Goal: {goal}")
    print(f"Model: {MODEL}")
    print(f"System prompt: {len(SYSTEM_PROMPT)} chars")
    print()

    # Call model
    print("Calling model...")
    raw = call_model(goal)
    print(f"Response: {len(raw)} chars")

    # Parse
    print("Parsing JSON...")
    try:
        payload = parse_response(raw)
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        print(f"Raw response:\n{raw[:2000]}")
        return 1

    files = payload.get("files", [])
    print(f"Files: {len(files)}")

    # Write to temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        written = write_files(project_dir, files)

        print(f"\nWritten {len(written)} files:")
        for w in written:
            print(f"  {w}")

        # Show file tree
        print(f"\nProject structure:")
        for f in sorted(project_dir.rglob("*")):
            if f.is_file():
                rel = f.relative_to(project_dir)
                size = f.stat().st_size
                print(f"  {rel} ({size} bytes)")

        # Check for required files
        required = ["package.json", "index.html"]
        for r in required:
            if (project_dir / r).exists():
                print(f"  [OK] {r}")
            else:
                print(f"  [MISSING] {r}")

        src_files = list((project_dir / "src").glob("*")) if (project_dir / "src").exists() else []
        print(f"  src/ files: {len(src_files)}")

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
