#!/usr/bin/env python3
"""Static security checks for Python (AST) and simple JS pattern heuristics."""

from __future__ import annotations

import ast
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


DANGEROUS_PY_CALLS = {"eval", "exec", "__import__"}
JS_RISKY = re.compile(
    r"\beval\s*\(|new\s+Function\s*\(|innerHTML\s*=|document\.write\s*\(",
    re.I,
)


def should_skip_dir(name: str) -> bool:
    return name in SKIP_DIRS or name.startswith(".")


def scan_python(path: Path) -> list[dict]:
    findings: list[dict] = []
    try:
        src = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(src, filename=str(path))
    except SyntaxError as e:
        return [{"path": str(path), "issue": "syntax_error", "detail": str(e)}]
    except OSError:
        return findings

    class Visitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call) -> None:
            name = None
            if isinstance(node.func, ast.Name):
                name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                name = node.func.attr
                if (
                    name == "compile"
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "re"
                ):
                    name = None
            if name in DANGEROUS_PY_CALLS:
                findings.append(
                    {
                        "path": str(path),
                        "line": getattr(node, "lineno", 0),
                        "issue": "dangerous_call",
                        "detail": name,
                    }
                )
            self.generic_visit(node)

    Visitor().visit(tree)
    return findings


def scan_javascript(path: Path) -> list[dict]:
    findings: list[dict] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return findings
    for i, line in enumerate(lines, start=1):
        if JS_RISKY.search(line):
            findings.append(
                {
                    "path": str(path),
                    "line": i,
                    "issue": "risky_js_pattern",
                    "detail": line.strip()[:200],
                }
            )
    return findings


def find_repo_root() -> Path:
    env = os.environ.get("WORKSPACE") or os.environ.get("CI_PROJECT_DIR")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parent.parent


def iter_scan_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    backend = root / "backend"
    if backend.is_dir():
        for dirpath, dirnames, filenames in os.walk(backend):
            dirnames[:] = [d for d in dirnames if not should_skip_dir(d)]
            for name in filenames:
                path = Path(dirpath) / name
                if "node_modules" in path.parts:
                    continue
                if name.endswith((".py", ".js")):
                    paths.append(path)
    ai_dir = root / "ai"
    if ai_dir.is_dir():
        for path in ai_dir.glob("*.py"):
            paths.append(path)
    return paths


def main() -> int:
    root = find_repo_root()
    all_findings: list[dict] = []

    for path in iter_scan_paths(root):
        if path.suffix.lower() == ".py":
            all_findings.extend(scan_python(path))
        elif path.suffix.lower() == ".js":
            all_findings.extend(scan_javascript(path))

    out = {
        "root": str(root),
        "summary": {"finding_count": len(all_findings)},
        "findings": all_findings,
    }
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
