"""Review step: send generated files to reviewer model, get issues + fixes."""

import json, os, re
from pathlib import Path
from openai import OpenAI

API_KEY = os.getenv("NVIDIA_API_KEY", "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")
BASE_URL = "https://integrate.api.nvidia.com/v1"
MODEL = "meta/llama-3.3-70b-instruct"
PROJECT = Path(r"D:\Vs Code\VS code\tic-tac-toe")

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

def files_to_text():
    parts = []
    for f in sorted(PROJECT.rglob("*")):
        if f.is_file() and ".autobots" not in str(f) and "node_modules" not in str(f):
            rel = f.relative_to(PROJECT)
            try:
                content = f.read_text(encoding="utf-8")
                parts.append(f"--- {rel} ---\n{content}")
            except:
                pass
    return "\n\n".join(parts)

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

def main():
    print("Collecting files...")
    files_text = files_to_text()
    print(f"Files text: {len(files_text)} chars")

    print("Reviewing...")
    raw = call_model(REVIEWER_PROMPT, REVIEWER_PROMPT + files_text)
    print(f"Review response: {len(raw)} chars")

    review = parse_json(raw)
    issues = review.get("issues", [])
    fixes = review.get("fixes", [])

    print(f"\nIssues found: {len(issues)}")
    for i, issue in enumerate(issues):
        print(f"  {i+1}. {issue}")

    print(f"Fixes: {len(fixes)}")
    for fix in fixes:
        path = fix.get("path", "")
        content = fix.get("content", "")
        target = (PROJECT / path) if path else None
        if target:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            print(f"  Applied fix: {path} ({len(content)} chars)")

    if not issues:
        print("\nNo issues found!")

    print("\nDone.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
