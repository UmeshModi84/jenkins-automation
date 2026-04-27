#!/usr/bin/env python3
"""Parse log files for errors/warnings; top signatures and remediation hints."""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter


def read_lines(path: str) -> list[str]:
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.readlines()


def classify(line: str) -> str | None:
    lower = line.lower()
    if "error" in lower:
        return "error"
    if "warn" in lower:
        return "warning"
    return None


def normalize_error(line: str) -> str:
    s = line.strip()
    s = re.sub(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}\S*", "<TS>", s)
    s = re.sub(r"\b0x[0-9a-f]+\b", "<HEX>", s, flags=re.I)
    s = re.sub(r"\b\d+\b", "<N>", s)
    return s[:240]


def suggestions(error_lines: list[str], warn_count: int) -> list[str]:
    hints: list[str] = []
    joined = "\n".join(error_lines[:50]).lower()

    if "econnrefused" in joined or "connection refused" in joined:
        hints.append(
            "Connection refused: verify the target host/port is reachable "
            "and the service is running (e.g. database or upstream API)."
        )
    if "enotfound" in joined or "getaddrinfo" in joined:
        hints.append(
            "DNS/hostname resolution failed: check DNS, /etc/hosts, "
            "and the hostname spelling in configuration."
        )
    if "eacces" in joined or "permission denied" in joined:
        hints.append(
            "Permission denied: run with correct user, fix file permissions, "
            "or adjust security context (SELinux/AppArmor)."
        )
    if "cannot find module" in joined or "module not found" in joined:
        hints.append(
            "Missing module: run dependency install (npm install / pip install) "
            "and verify NODE_PATH or PYTHONPATH."
        )
    if "out of memory" in joined or "ENOMEM" in joined:
        hints.append(
            "Out of memory: increase container/host memory limits or reduce "
            "batch size / concurrency."
        )
    if "syntaxerror" in joined or "unexpected token" in joined:
        hints.append(
            "Syntax error: fix the reported file/line; ensure the runtime "
            "matches the language version used in development."
        )
    if warn_count > 0 and not hints:
        hints.append(
            f"Found {warn_count} warning line(s): review logs for deprecations "
            "and upgrade libraries or fix usage flagged by maintainers."
        )
    if not hints:
        hints.append(
            "Review the top error signatures below; grep the codebase for the "
            "message text and add targeted tests or guards around failing calls."
        )
    return hints


def analyze_log_file(path: str) -> dict:
    lines = read_lines(path)
    error_lines: list[str] = []
    warn_lines: list[str] = []

    for line in lines:
        kind = classify(line)
        if kind == "error":
            error_lines.append(line.rstrip("\n"))
        elif kind == "warning":
            warn_lines.append(line.rstrip("\n"))

    counter = Counter(normalize_error(line) for line in error_lines)
    top10 = counter.most_common(10)
    return {
        "path": path,
        "total_lines": len(lines),
        "error_line_count": len(error_lines),
        "warn_line_count": len(warn_lines),
        "top_errors": top10,
        "suggestions": suggestions(error_lines, len(warn_lines)),
    }


def format_report(result: dict) -> str:
    lines_out: list[str] = []
    lines_out.append("=== Log analysis ===")
    lines_out.append(f"File: {result['path']}")
    lines_out.append(f"Total lines: {result['total_lines']}")
    lines_out.append(
        f"Lines matching 'error' (case insensitive): {result['error_line_count']}"
    )
    lines_out.append(f"Lines matching 'warn': {result['warn_line_count']}")
    lines_out.append("")
    lines_out.append("--- Top 10 errors (normalized) ---")
    top = result["top_errors"]
    if not top:
        lines_out.append("(no error lines detected)")
    else:
        for i, (msg, count) in enumerate(top, start=1):
            lines_out.append(f"{i:2}. [{count}x] {msg}")
    lines_out.append("")
    lines_out.append("--- Suggestions ---")
    for hint in result["suggestions"]:
        lines_out.append(f"- {hint}")
    return "\n".join(lines_out)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze application logs.")
    parser.add_argument(
        "logfile",
        help="Path to the log file produced by the application or container.",
    )
    args = parser.parse_args()

    try:
        result = analyze_log_file(args.logfile)
    except OSError as e:
        print(f"Failed to read log file: {e}", file=sys.stderr)
        return 1

    print(format_report(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
