#!/usr/bin/env python3
"""Apply safe mechanical fixes (strip trailing spaces/tabs per line, ensure final newline)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


SKIP_DIRS = {"node_modules", ".git", "venv", ".venv", "__pycache__", ".pytest_cache"}


def should_skip_dir(name: str) -> bool:
    return name in SKIP_DIRS or name.startswith(".")


def fix_file(path: Path, dry_run: bool) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False

    ends_with_nl = text.endswith("\n")
    raw_lines = text.splitlines()
    new_lines = [line.rstrip(" \t\r") for line in raw_lines]
    new_text = "\n".join(new_lines)
    if ends_with_nl or raw_lines:
        new_text += "\n"

    if new_text == text:
        return False
    if not dry_run:
        path.write_text(new_text, encoding="utf-8", newline="\n")
    return True


def find_repo_root() -> Path:
    env = os.environ.get("WORKSPACE") or os.environ.get("CI_PROJECT_DIR")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Safe whitespace fixes for source files.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report files that would change without writing.",
    )
    args = parser.parse_args()

    root = find_repo_root()
    targets: list[Path] = []
    backend = root / "backend"
    if backend.is_dir():
        for dirpath, dirnames, filenames in os.walk(backend):
            dirnames[:] = [d for d in dirnames if not should_skip_dir(d)]
            for name in filenames:
                if name.endswith((".js", ".json", ".cjs")):
                    targets.append(Path(dirpath) / name)

    ai_dir = root / "ai"
    if ai_dir.is_dir():
        for p in ai_dir.glob("*.py"):
            targets.append(p)

    changed = 0
    for path in sorted(set(targets)):
        if fix_file(path, args.dry_run):
            changed += 1
            print(("would fix " if args.dry_run else "fixed ") + str(path))

    print(json.dumps({"changed_files": changed, "dry_run": args.dry_run}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
