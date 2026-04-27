#!/usr/bin/env python3
"""Small GitHub REST helpers (token from GITHUB_TOKEN or GH_TOKEN)."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def _token() -> str | None:
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")


def github_request(
    path: str,
    method: str = "GET",
    data: dict | None = None,
    token: str | None = None,
) -> tuple[int, dict | list]:
    tok = token or _token()
    if not tok:
        raise RuntimeError("Set GITHUB_TOKEN or GH_TOKEN for GitHub API access.")

    url = urllib.parse.urljoin("https://api.github.com/", path.lstrip("/"))
    body = None if data is None else json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {tok}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "test-ai-cicd-automation",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            status = resp.status
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub HTTP {e.code}: {raw}") from e

    if not raw:
        return status, {}
    parsed = json.loads(raw)
    return status, parsed


def get_pull_request(owner: str, repo: str, number: int) -> dict:
    _, pr = github_request(f"/repos/{owner}/{repo}/pulls/{number}")
    if not isinstance(pr, dict):
        raise RuntimeError("Unexpected PR payload")
    return pr


def list_pull_request_files(owner: str, repo: str, number: int) -> list[dict]:
    _, files = github_request(f"/repos/{owner}/{repo}/pulls/{number}/files")
    if not isinstance(files, list):
        raise RuntimeError("Unexpected files payload")
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch PR metadata (JSON).")
    parser.add_argument("owner")
    parser.add_argument("repo")
    parser.add_argument("pr_number", type=int)
    args = parser.parse_args()

    pr = get_pull_request(args.owner, args.repo, args.pr_number)
    print(json.dumps(pr, indent=2)[:8000])
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        raise SystemExit(1)
