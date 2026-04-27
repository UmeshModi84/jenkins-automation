#!/usr/bin/env python3
"""Minimal OpenAI-compatible chat helper (HTTPS, env OPENAI_API_KEY)."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def chat_completion(
    messages: list[dict[str, str]],
    model: str | None = None,
    api_key: str | None = None,
    base_url: str = "https://api.openai.com/v1",
) -> dict:
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        return {
            "mock": True,
            "content": (
                "OPENAI_API_KEY is not set. In CI, export the key or inject via "
                "Jenkins credentials. This is a placeholder response."
            ),
        }

    mdl = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    url = f"{base_url.rstrip('/')}/chat/completions"
    body = json.dumps(
        {"model": mdl, "messages": messages, "temperature": 0.2}
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI HTTP {e.code}: {err}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"OpenAI request failed: {e}") from e

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Unexpected API response: {data!r}") from e
    return {"mock": False, "content": content, "raw": data}


def main() -> int:
    parser = argparse.ArgumentParser(description="Send one user message to OpenAI.")
    parser.add_argument("message", nargs="?", default="Say hello in one sentence.")
    parser.add_argument("--model", default=None, help="Override OPENAI_MODEL.")
    args = parser.parse_args()

    result = chat_completion(
        [{"role": "user", "content": args.message}],
        model=args.model,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        raise SystemExit(1)
