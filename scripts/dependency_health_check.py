import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from shutil import which


@dataclass
class CheckResult:
    command: list[str]
    return_code: int
    stdout: str
    stderr: str


def _run(command: list[str]) -> CheckResult:
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    return CheckResult(
        command=command,
        return_code=completed.returncode,
        stdout=completed.stdout.strip(),
        stderr=completed.stderr.strip(),
    )


def _print_section(title: str, body: str) -> None:
    print(f"\n=== {title} ===")
    print(body or "(no output)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Dependency health checks for local and CI use")
    parser.add_argument(
        "--requirements",
        default="requirements.txt",
        help="Path to the requirements file to audit",
    )
    parser.add_argument(
        "--fail-on-outdated",
        action="store_true",
        help="Fail when outdated packages are detected",
    )
    args = parser.parse_args()

    if not Path(args.requirements).exists():
        print(f"requirements file not found: {args.requirements}")
        return 2

    pip_audit_executable = which("pip-audit")
    if pip_audit_executable is None:
        candidate = Path(sys.executable).with_name("pip-audit.exe")
        if candidate.exists():
            pip_audit_executable = str(candidate)
    audit_command = (
        [pip_audit_executable, "-r", args.requirements, "-f", "json"]
        if pip_audit_executable is not None
        else [sys.executable, "-m", "pip_audit", "-r", args.requirements, "-f", "json"]
    )
    audit = _run(audit_command)
    if audit.return_code != 0 and not audit.stdout:
        _print_section("pip-audit stderr", audit.stderr)
        return audit.return_code

    vulnerabilities = []
    if audit.stdout:
        try:
            payload = json.loads(audit.stdout)
            vulnerabilities = payload.get("vulns", [])
        except json.JSONDecodeError:
            _print_section("pip-audit output", audit.stdout)
            _print_section("pip-audit stderr", audit.stderr)
            return 1

    outdated = _run([sys.executable, "-m", "pip", "list", "--outdated", "--format=json"])
    if outdated.return_code != 0:
        _print_section("pip outdated stderr", outdated.stderr)
        return outdated.return_code

    outdated_rows = json.loads(outdated.stdout) if outdated.stdout else []

    _print_section(
        "Vulnerability Summary",
        f"Known vulnerabilities: {len(vulnerabilities)}",
    )
    if vulnerabilities:
        _print_section("Vulnerabilities", json.dumps(vulnerabilities, indent=2))

    _print_section(
        "Outdated Summary",
        f"Outdated packages: {len(outdated_rows)}",
    )
    if outdated_rows:
        _print_section("Outdated Packages", json.dumps(outdated_rows, indent=2))

    if vulnerabilities:
        return 1
    if args.fail_on_outdated and outdated_rows:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
