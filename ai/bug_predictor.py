#!/usr/bin/env python3
"""Heuristic bug-risk scoring from source complexity and smell patterns."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


SKIP_DIRS = {
    "node_modules",
    ".git",
    "venv",
    ".venv",
    "__pycache__",
    ".pytest_cache",
}

RISKY_JS = [
    (r"catch\s*\(\s*\)\s*\{", "empty_catch", 25),
    (r"catch\s*\(\s*_\s*\)\s*\{\s*\}", "swallowed_error", 20),
    (r"\bprocess\.exit\s*\(", "abrupt_exit", 10),
    (r"!=\s*null|==\s*null", "loose_null_check", 5),
]

RISKY_PY = [
    (r"except\s*:", "bare_except", 30),
    (r"except\s+Exception\s*:\s*pass", "silent_exception", 25),
]


def should_skip_dir(name: str) -> bool:
    return name in SKIP_DIRS or name.startswith(".")


def score_file(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {"path": str(path), "score": 0, "signals": []}

    signals: list[dict] = []
    score = 0
    suffix = path.suffix.lower()
    patterns = RISKY_JS if suffix == ".js" else RISKY_PY if suffix == ".py" else []

    for pat, name, weight in patterns:
        for m in re.finditer(pat, text, re.MULTILINE):
            signals.append({"name": name, "line": text[: m.start()].count("\n") + 1})
            score += weight

    lines = max(1, text.count("\n"))
    score += min(15, lines // 200)
    return {"path": str(path), "score": int(score), "signals": signals}


def find_repo_root() -> Path:
    env = os.environ.get("WORKSPACE") or os.environ.get("CI_PROJECT_DIR")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parent.parent


def main() -> int:
    root = find_repo_root()
    scored: list[dict] = []

    for dirpath, dirnames, filenames in os.walk(root / "backend"):
        dirnames[:] = [d for d in dirnames if not should_skip_dir(d)]
        for name in filenames:
            if not name.endswith((".js", ".py")):
                continue
            path = Path(dirpath) / name
            if "node_modules" in path.parts:
                continue
            scored.append(score_file(path))

    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[:15]
    print(
        json.dumps(
            {
                "root": str(root),
                "summary": {
                    "files_scored": len(scored),
                    "highest_risk": top[0] if top else None,
                },
                "top_risk_files": top,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
