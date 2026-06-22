from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from typing import Any


@dataclass
class DiagnosticCheck:
    name: str
    passed: bool
    message: str


def check_api_key() -> DiagnosticCheck:
    key = os.environ.get("NVIDIA_API_KEY", "")
    if not key:
        return DiagnosticCheck(
            name="API Key",
            passed=False,
            message="NVIDIA_API_KEY not set. Run: set NVIDIA_API_KEY=your_key",
        )
    if len(key) < 10:
        return DiagnosticCheck(
            name="API Key",
            passed=False,
            message="NVIDIA_API_KEY appears too short.",
        )
    return DiagnosticCheck(
        name="API Key",
        passed=True,
        message=f"NVIDIA_API_KEY set (ends with ...{key[-4:]})",
    )


def check_connectivity() -> DiagnosticCheck:
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "NUL", "-w", "%{http_code}", "https://integrate.api.nvidia.com/v1/models"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        code = result.stdout.strip()
        if code == "200":
            return DiagnosticCheck(name="Connectivity", passed=True, message="NVIDIA API reachable")
        return DiagnosticCheck(
            name="Connectivity",
            passed=False,
            message=f"NVIDIA API returned HTTP {code}",
        )
    except Exception as e:
        return DiagnosticCheck(
            name="Connectivity",
            passed=False,
            message=f"Cannot reach NVIDIA API: {e}",
        )


def check_python_version() -> DiagnosticCheck:
    major, minor = os.sys.version_info[:2]
    if major >= 3 and minor >= 11:
        return DiagnosticCheck(
            name="Python Version",
            passed=True,
            message=f"Python {major}.{minor} (OK)",
        )
    return DiagnosticCheck(
        name="Python Version",
        passed=False,
        message=f"Python {major}.{minor} (requires 3.11+)",
    )


def check_package_installed() -> DiagnosticCheck:
    try:
        result = subprocess.run(
            ["pip", "show", "autobot-swarm"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return DiagnosticCheck(name="Package", passed=True, message="autobot-swarm installed")
        return DiagnosticCheck(name="Package", passed=False, message="autobot-swarm not installed")
    except Exception as e:
        return DiagnosticCheck(name="Package", passed=False, message=str(e))


def run_doctor() -> list[DiagnosticCheck]:
    checks = [
        check_python_version(),
        check_api_key(),
        check_connectivity(),
        check_package_installed(),
    ]
    return checks


def format_doctor_results(checks: list[DiagnosticCheck]) -> str:
    lines = ["Autobots Doctor Results:"]
    for check in checks:
        status = "PASS" if check.passed else "FAIL"
        lines.append(f"  [{status}] {check.name}: {check.message}")
    passed = sum(1 for c in checks if c.passed)
    lines.append(f"\n{passed}/{len(checks)} checks passed")
    return "\n".join(lines)
