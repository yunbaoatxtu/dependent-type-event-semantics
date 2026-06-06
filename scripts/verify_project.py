#!/usr/bin/env python3
"""Run the repository's deterministic verification checks."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYCACHE = ROOT / ".pycache"


def run(label: str, command: list[str]) -> None:
    print(f"==> {label}")
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    run("unit tests", [sys.executable, "-m", "unittest", "discover", "-v"])
    run(
        "python compile check",
        [
            sys.executable,
            "-X",
            f"pycache_prefix={PYCACHE}",
            "-m",
            "py_compile",
            "translator/dependent_type_event_translator.py",
            "tests/test_translator.py",
            "scripts/generate_formalization.py",
            "scripts/check_formalization.py",
        ],
    )
    run("formalization consistency", [sys.executable, "scripts/check_formalization.py"])
    print("all deterministic checks passed")


if __name__ == "__main__":
    main()
