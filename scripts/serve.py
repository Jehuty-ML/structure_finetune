#!/usr/bin/env python3
"""Minimal API sketch: validate a raw generation into a VoiceTurn payload."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from structured_llm.serve import parse_generation_to_response


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--text-file",
        help="Path to a raw model generation; if omitted, read stdin",
    )
    parser.add_argument(
        "--schema",
        default=str(ROOT / "schemas" / "echo_turn.schema.json"),
    )
    args = parser.parse_args()

    if args.text_file:
        text = Path(args.text_file).read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()

    resp = parse_generation_to_response(text, schema_path=args.schema)
    print(json.dumps(resp, indent=2, ensure_ascii=False))
    raise SystemExit(0 if resp.get("ok") else 1)


if __name__ == "__main__":
    main()
