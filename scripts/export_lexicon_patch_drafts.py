#!/usr/bin/env python3
"""Export manual result-state lexicon patch drafts for one sentence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from web.app import LEXICON_PATCH_DRAFTS_SCHEMA, build_lexicon_patch_bundle  # noqa: E402


SCHEMA_VERSION = LEXICON_PATCH_DRAFTS_SCHEMA


def build_patch_bundle(sentence: str, require_coq: bool = False) -> dict:
    return build_lexicon_patch_bundle(sentence, require_coq=require_coq)


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
