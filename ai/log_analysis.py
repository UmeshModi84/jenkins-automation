#!/usr/bin/env python3
"""CLI entry used by Jenkins; delegates to log_analyzer."""

from __future__ import annotations

import sys
from pathlib import Path

_ai_dir = Path(__file__).resolve().parent
if str(_ai_dir) not in sys.path:
    sys.path.insert(0, str(_ai_dir))

from log_analyzer import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
