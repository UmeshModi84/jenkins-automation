#!/usr/bin/env python3
"""Generate basic supertest/Mocha stubs from Express route declarations."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path


ROUTE_RE = re.compile(
    r"app\.(get|post|put|delete|patch)\s*\(\s*['\"]([^'\"]+)['\"]",
    re.I,
)


def find_repo_root() -> Path:
    env = os.environ.get("WORKSPACE") or os.environ.get("CI_PROJECT_DIR")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parent.parent


def extract_routes(index_path: Path) -> list[tuple[str, str]]:
    text = index_path.read_text(encoding="utf-8", errors="replace")
    return [(m.group(1).upper(), m.group(2)) for m in ROUTE_RE.finditer(text)]


def render_mocha(routes: list[tuple[str, str]]) -> str:
    lines = [
        "'use strict';",
        "",
        "const request = require('supertest');",
        "const { app } = require('../src/index.js');",
        "",
        "describe('generated smoke routes', function () {",
    ]
    for method, route in routes:
        name = f"{method} {route}"
        lines.append(f"  it('{name}', async function () {{")
        if method == "GET":
            lines.append(
                f"    const res = await request(app).{method.lower()}('{route}');"
            )
            lines.append("    if (res.status >= 500) throw new Error(res.text);")
        else:
            lines.append(
                f"    const res = await request(app).{method.lower()}('{route}')"
                ".send({});"
            )
            lines.append("    if (res.status >= 500) throw new Error(res.text);")
        lines.append("  });")
    lines.append("});")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Mocha route smoke tests.")
    parser.add_argument(
        "--out",
        default="",
        help="Write to this path instead of stdout.",
    )
    args = parser.parse_args()

    root = find_repo_root()
    index = root / "backend" / "src" / "index.js"
    if not index.is_file():
        print(f"Missing {index}", file=sys.stderr)
        return 1

    routes = extract_routes(index)
    body = render_mocha(routes)
    if args.out:
        Path(args.out).write_text(body, encoding="utf-8")
        print(f"Wrote {args.out}")
    else:
        print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
