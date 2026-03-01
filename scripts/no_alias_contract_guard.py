from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCAN_ROOTS = [
    REPO_ROOT / "app",
    REPO_ROOT / "core",
    REPO_ROOT / "engine",
    REPO_ROOT / "adapters",
]
TOP_LEVEL_FILES = [
    REPO_ROOT / "main.py",
]

PATTERNS = {
    "field_or_param_alias": re.compile(r'\balias\s*=\s*"'),
    "model_dump_by_alias": re.compile(r"\bmodel_dump\(\s*by_alias\s*=\s*True"),
    "response_model_by_alias": re.compile(r"\bresponse_model_by_alias\s*=\s*True"),
    "populate_by_name": re.compile(r"\bpopulate_by_name\b"),
    "legacy_client_term": re.compile(r"\bcif_id\b"),
    "legacy_booking_center_term": re.compile(r"\bbooking_center\b"),
}


def _iter_source_files() -> list[Path]:
    files: list[Path] = []
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        files.extend(root.rglob("*.py"))
    for file_path in TOP_LEVEL_FILES:
        if file_path.exists():
            files.append(file_path)
    return files


def main() -> int:
    findings: list[str] = []
    for file_path in _iter_source_files():
        content = file_path.read_text(encoding="utf-8")
        for idx, line in enumerate(content.splitlines(), start=1):
            for rule_name, pattern in PATTERNS.items():
                if pattern.search(line):
                    rel = file_path.relative_to(REPO_ROOT)
                    findings.append(f"{rel}:{idx}: {rule_name}: {line.strip()}")

    if findings:
        print("No-alias contract guard failed. Remove alias-based API patterns:")
        for finding in findings:
            print(f" - {finding}")
        return 1

    print("No-alias contract guard passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
