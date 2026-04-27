#!/usr/bin/env python3
"""Detect numeric outliers in simple build/metric lines (stdin or file)."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from statistics import mean, pstdev


NUMERIC = re.compile(r"-?\d+(?:\.\d+)?")


def extract_numbers(line: str) -> list[float]:
    return [float(m.group(0)) for m in NUMERIC.finditer(line)]


def zscore_anomaly(values: list[float], threshold: float = 2.5) -> list[int]:
    if len(values) < 3:
        return []
    m = mean(values)
    sd = pstdev(values)
    if sd == 0:
        return []
    out: list[int] = []
    for i, v in enumerate(values):
        z = abs((v - m) / sd)
        if z >= threshold and not math.isnan(z):
            out.append(i)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read lines with numbers; flag lines whose values are outliers."
    )
    parser.add_argument(
        "input_file",
        nargs="?",
        default="-",
        help="Path to metrics log or '-' for stdin.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=2.5,
        help="Absolute z-score above which a point is anomalous.",
    )
    args = parser.parse_args()

    if args.input_file == "-":
        text = sys.stdin.read()
    else:
        with open(args.input_file, encoding="utf-8", errors="replace") as f:
            text = f.read()

    lines = [ln.rstrip("\n") for ln in text.splitlines() if ln.strip()]
    per_line_first: list[float] = []
    line_refs: list[str] = []
    for ln in lines:
        nums = extract_numbers(ln)
        if nums:
            per_line_first.append(nums[0])
            line_refs.append(ln[:500])

    idx_bad = zscore_anomaly(per_line_first, args.threshold)
    anomalies = [
        {"line_index": i, "value": per_line_first[i], "text": line_refs[i]}
        for i in idx_bad
    ]

    print(
        json.dumps(
            {
                "lines_with_numbers": len(per_line_first),
                "anomaly_count": len(anomalies),
                "anomalies": anomalies,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
