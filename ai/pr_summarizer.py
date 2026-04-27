#!/usr/bin/env python3
"""Build a short PR summary from GitHub file list + optional OpenAI polish."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_ai_dir = Path(__file__).resolve().parent
if str(_ai_dir) not in sys.path:
    sys.path.insert(0, str(_ai_dir))

from github_utils import get_pull_request, list_pull_request_files  # noqa: E402
from openai_chat import chat_completion  # noqa: E402


def build_text_summary(owner: str, repo: str, number: int, max_files: int = 40) -> str:
    pr = get_pull_request(owner, repo, number)
    files = list_pull_request_files(owner, repo, number)[:max_files]
    lines = [
        f"PR #{number}: {pr.get('title', '')}",
        f"Author: {pr.get('user', {}).get('login')}",
        f"State: {pr.get('state')} mergeable={pr.get('mergeable')}",
        "",
        "Changed files (truncated):",
    ]
    for f in files:
        status = f.get("status")
        path = f.get("filename")
        additions = f.get("additions", 0)
        deletions = f.get("deletions", 0)
        lines.append(f"  - [{status}] {path} (+{additions}/-{deletions})")
    body = (pr.get("body") or "").strip()
    if body:
        lines.extend(["", "Description (truncated):", body[:2000]])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize a GitHub pull request.")
    parser.add_argument("owner")
    parser.add_argument("repo")
    parser.add_argument("pr_number", type=int)
    parser.add_argument(
        "--use-openai",
        action="store_true",
        help="If OPENAI_API_KEY is set, ask the model for a one-paragraph summary.",
    )
    args = parser.parse_args()

    summary = build_text_summary(args.owner, args.repo, args.pr_number)
    print("=== PR summary (deterministic) ===")
    print(summary)

    if args.use_openai and os.environ.get("OPENAI_API_KEY"):
        prompt = (
            "Summarize this pull request for a release engineer in one short "
            "paragraph. Focus on risk and testing.\n\n" + summary
        )
        out = chat_completion([{"role": "user", "content": prompt}])
        print("\n=== OpenAI summary ===")
        print(out.get("content", json.dumps(out)))

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        raise SystemExit(1)
