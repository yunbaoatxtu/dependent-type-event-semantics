#!/usr/bin/env python3
"""Generate Lean/Coq-style shallow embedding files from checked examples."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from translator.dependent_type_event_translator import export_module, translate


EXAMPLE_NAMES = [
    "example_butter.json",
    "example_eat_omission.json",
    "example_knock_twice.json",
    "example_break_result.json",
]


def load_results() -> list[dict]:
    examples_dir = ROOT / "translator" / "examples"
    results = []
    for name in EXAMPLE_NAMES:
        data = json.loads((examples_dir / name).read_text(encoding="utf-8"))
        result = translate(data)
        if not result["type_check"]["ok"]:
            raise ValueError(f"{name} failed type_check: {result['type_check']['errors']}")
        results.append(result)
    return results


def main() -> None:
    out_dir = ROOT / "formalization"
    out_dir.mkdir(exist_ok=True)
    results = load_results()
    (out_dir / "DependentTypeEventSemantics.lean").write_text(
        export_module(results, "lean"),
        encoding="utf-8",
    )
    (out_dir / "DependentTypeEventSemantics.v").write_text(
        export_module(results, "coq"),
        encoding="utf-8",
    )
    print(f"Wrote {out_dir / 'DependentTypeEventSemantics.lean'}")
    print(f"Wrote {out_dir / 'DependentTypeEventSemantics.v'}")


if __name__ == "__main__":
    main()
