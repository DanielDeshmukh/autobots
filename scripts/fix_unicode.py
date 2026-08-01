import re
from pathlib import Path

file_path = Path(__file__).parent.parent / "autobots" / "swarm_pipeline.py"
content = file_path.read_text(encoding="utf-8")

# Replace common Unicode with ASCII
replacements = {
    '\u2500': '-',  # ─
    '\u2501': '=',  # ━
    '\u2502': '|',  # │
    '\u2503': '#',  # ┃
    '\u2192': '->', # →
    '\u2713': '[OK]', # ✓
    '\u2717': '[FAIL]', # ✗
    '\u25cb': '[WAIT]', # ○
    '\u2014': '--', # —
    '\u2013': '-',  # –
    '\u2018': "'",  # '
    '\u2019': "'",  # '
    '\u201c': '"',  # "
    '\u201d': '"',  # "
    '\u2026': '...', # …
}

for old, new in replacements.items():
    content = content.replace(old, new)

file_path.write_text(content, encoding="utf-8")
print(f"Fixed Unicode chars in {file_path}")
