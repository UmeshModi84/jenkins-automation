#!/usr/bin/env python3
"""Recursive static scan of .js and .py files for risky patterns."""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


SKIP_DIRS = {
    "node_modules",
    ".git",
    "venv",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "dist",
    "build",
    ".next",
    "coverage",
}


@dataclass
class Finding:
    category: str
    path: str
    line: int
    snippet: str


@dataclass
class Report:
    secret_hits: list[Finding] = field(default_factory=list)
    console_log_hits: list[Finding] = field(default_factory=list)
    todo_hits: list[Finding] = field(default_factory=list)


SECRET_PATTERN = re.compile(
    r"(?i)(password|secret|api_key)\s*[:=]\s*['\"]?[^\s'\"]{3,}",
)
CONSOLE_LOG_PATTERN = re.compile(r"\bconsole\.log\s*\(")
COMMENT_MARKER_PATTERN = re.compile(r"(?i)\bTODO\b")


def should_skip_dir(name: str) -> bool:
    return name in SKIP_DIRS or name.startswith(".")


def scan_file(path: Path, report: Report) -> None:
    suffix = path.suffix.lower()
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return

    lines = text.splitlines()
    for i, line in enumerate(lines, start=1):
        if suffix == ".js":
            for m in CONSOLE_LOG_PATTERN.finditer(line):
                report.console_log_hits.append(
                    Finding("console.log", str(path), i, line.strip()[:200])
                )
        for m in SECRET_PATTERN.finditer(line):
            report.secret_hits.append(
                Finding("hardcoded_secret", str(path), i, line.strip()[:200])
            )
        for m in COMMENT_MARKER_PATTERN.finditer(line):
            report.todo_hits.append(
                Finding("todo_in_source", str(path), i, line.strip()[:200])
            )


def find_repo_root() -> Path:
    env = os.environ.get("WORKSPACE") or os.environ.get("CI_PROJECT_DIR")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parent.parent


def enrich_with_openai(report: dict) -> None:
    """Optional LLM summary; never raises — failures end up in report['openai_review']."""
    api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if not api_key:
        report["openai_review"] = {"enabled": False, "reason": "OPENAI_API_KEY not set"}
        return
    try:
        from openai import OpenAI
    except ImportError:
        report["openai_review"] = {
            "enabled": False,
            "reason": "openai package missing; run: pip install -r ai/requirements.txt",
        }
        return

    model = (os.environ.get("OPENAI_MODEL") or "gpt-4o-mini").strip()
    blob = json.dumps(report, indent=2)
    if len(blob) > 16000:
        blob = blob[:16000] + "\n... [truncated for LLM context]"

    prompt = (
        "You are a senior engineer reviewing static scan output. "
        "Prioritize by severity. Reply in markdown: a one-line summary, then numbered action items (max 8).\n\n"
        f"```json\n{blob}\n```"
    )
    try:
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Security-oriented code review. Be concise."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=900,
            temperature=0.2,
        )
        text = (resp.choices[0].message.content or "").strip()
        report["openai_review"] = {"enabled": True, "model": model, "markdown": text}
    except Exception as e:
        report["openai_review"] = {"enabled": True, "model": model, "error": str(e)}


def main() -> int:
    root = find_repo_root()
    report = Report()

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not should_skip_dir(d)]
        for name in filenames:
            if not name.endswith((".js", ".py")):
                continue
            path = Path(dirpath) / name
            if "node_modules" in path.parts or ".git" in path.parts:
                continue
            scan_file(path, report)

    out = {
        "root": str(root),
        "summary": {
            "hardcoded_secret_pattern_hits": len(report.secret_hits),
            "console_log_hits": len(report.console_log_hits),
            "todo_hits": len(report.todo_hits),
        },
        "findings": {
            "hardcoded_password_secret_api_key": [
                {"path": f.path, "line": f.line, "snippet": f.snippet}
                for f in report.secret_hits
            ],
            "console_log": [
                {"path": f.path, "line": f.line, "snippet": f.snippet}
                for f in report.console_log_hits
            ],
            "todo_comments": [
                {"path": f.path, "line": f.line, "snippet": f.snippet}
                for f in report.todo_hits
            ],
        },
    }

    enrich_with_openai(out)

    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
