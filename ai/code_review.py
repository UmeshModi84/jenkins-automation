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

    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
