#!/usr/bin/env python3
"""Export manual result-state lexicon patch drafts for one sentence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from web.app import analyze_sentence  # noqa: E402


SCHEMA_VERSION = "lexicon_patch_drafts.v1"


def build_patch_bundle(sentence: str, require_coq: bool = False) -> dict[str, Any]:
    result = analyze_sentence(sentence, require_coq=require_coq)
    diagnostics = result.get("diagnostics", {})
    drafts = result.get("lexicon_patch_drafts", [])
    return {
        "schema_version": SCHEMA_VERSION,
        "input_sentence": result.get("input_sentence", sentence.strip()),
        "ok": bool(result.get("ok")),
        "diagnostics": {
            "summary": diagnostics.get("summary"),
            "failure_stage": diagnostics.get("failure_stage"),
            "manual_repair_required": diagnostics.get("manual_repair_required", False),
            "lexicon_patch_draft_count": diagnostics.get("lexicon_patch_draft_count", 0),
        },
        "requires_human_choice": any(
            draft.get("requires_human_choice") for draft in drafts
        ),
        "can_auto_apply": bool(drafts)
        and all(draft.get("can_auto_apply") for draft in drafts),
        "lexicon_patch_drafts": drafts,
        "conclusion": result.get("conclusion", ""),
        "error": result.get("error"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export human-gated STATE_LEXICON repair drafts for a sentence."
    )
    parser.add_argument("--sentence", required=True, help="Natural-language sentence to analyze.")
    parser.add_argument(
        "--require-coq",
        action="store_true",
        help="Require the same external Coq/Rocq check used by the web pipeline.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        help="Optional JSON output path. Defaults to stdout.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    bundle = build_patch_bundle(args.sentence, require_coq=args.require_coq)
    encoded = json.dumps(bundle, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.write_text(encoded, encoding="utf-8")
    else:
        sys.stdout.write(encoded)


if __name__ == "__main__":
    main()
