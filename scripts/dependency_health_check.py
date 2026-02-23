#!/usr/bin/env python
"""Basic dependency freshness checker used by local/CI gates."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--requirements", required=True, help="Path to requirements file")
    parser.add_argument(
        "--fail-on-outdated",
        action="store_true",
        help="Fail if outdated dependencies are detected",
    )
    args = parser.parse_args()

    req = Path(args.requirements)
    if not req.exists():
        print(f"requirements file not found: {req}")
        return 2

    proc = _run([sys.executable, "-m", "pip", "list", "--outdated", "--format=json"])
    if proc.returncode != 0:
        print(proc.stdout.strip())
        print(proc.stderr.strip())
        return proc.returncode

    outdated = json.loads(proc.stdout or "[]")
    if not outdated:
        print("dependency_health_check: no outdated packages detected")
        return 0

    print("dependency_health_check: outdated packages detected")
    for dep in outdated:
        print(f"- {dep['name']}: {dep['version']} -> {dep['latest_version']}")

    return 1 if args.fail_on_outdated else 0


if __name__ == "__main__":
    raise SystemExit(main())
