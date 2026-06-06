#!/usr/bin/env python3
"""Run the repository's deterministic verification checks."""

from __future__ import annotations

import subprocess
import sys
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYCACHE = ROOT / ".pycache"
COQ_FILE = ROOT / "formalization" / "DependentTypeEventSemantics.v"
ROCQ_ENV = Path(
    "/Applications/Rocq-Platform~9.0~2025.08.app/Contents/Resources/bin/coq-env.sh"
)


def run(label: str, command: list[str]) -> None:
    print(f"==> {label}")
    subprocess.run(command, cwd=ROOT, check=True)


def run_optional_coq_check() -> None:
    if shutil.which("coqc"):
        run("Coq scaffold check", ["coqc", str(COQ_FILE)])
        return

    if ROCQ_ENV.exists():
        run(
            "Coq scaffold check",
            [
                "/bin/zsh",
                "-lc",
                f'eval "$({ROCQ_ENV})" && coqc "{COQ_FILE}"',
            ],
        )
        return

    print("==> Coq scaffold check skipped: coqc not found")


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
    run_optional_coq_check()
    print("all deterministic checks passed")


if __name__ == "__main__":
    main()
