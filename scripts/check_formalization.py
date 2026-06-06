#!/usr/bin/env python3
"""Check that generated formalization scaffolds match current examples."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEAN_FILE = ROOT / "formalization" / "DependentTypeEventSemantics.lean"
COQ_FILE = ROOT / "formalization" / "DependentTypeEventSemantics.v"


def main() -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "generate_formalization.py")],
        check=True,
        capture_output=True,
        text=True,
    )

    lean = LEAN_FILE.read_text(encoding="utf-8")
    coq = COQ_FILE.read_text(encoding="utf-8")

    checks = {
        "lean declarations": "constant Entity : Type" in lean,
        "coq declarations": "Parameter Entity : Type." in coq,
        "lean check commands": "#check example_4" in lean,
        "coq check commands": "Check example_4." in coq,
        "lean unknown state normalized": "Transition vase unknown_state broken" in lean,
        "coq unknown state normalized": "Transition vase unknown_state broken" in coq,
        "no raw transition placeholder": "Transition vase _ broken" not in lean
        and "Transition vase _ broken" not in coq,
    }

    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        for name in failed:
            print(f"FAILED: {name}", file=sys.stderr)
        raise SystemExit(1)

    print("formalization scaffolds are consistent")


if __name__ == "__main__":
    main()
