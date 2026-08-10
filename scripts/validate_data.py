#!/usr/bin/env python3
"""Validate SFT rows against the Echo multi-block contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from structured_llm.contract import validate_turn
from structured_llm.data import iter_sft_rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, help="JSON array of {id,input,output}")
    parser.add_argument(
        "--schema",
        default=str(ROOT / "schemas" / "echo_turn.schema.json"),
        help="JSON Schema for the JSON block",
    )
    parser.add_argument("--json-out", default="", help="Optional report path")
    args = parser.parse_args()

    rows = list(iter_sft_rows(args.data))
    report = []
    ok_n = 0
    for row in rows:
        vr = validate_turn(row["output"], schema_path=args.schema)
        report.append(
            {
                "id": row.get("id"),
                "ok": vr.ok,
                "errors": vr.errors,
                "warnings": vr.warnings,
            }
        )
        if vr.ok:
            ok_n += 1
        else:
            print(f"FAIL {row.get('id')}: {vr.errors}")

    rate = ok_n / len(rows) if rows else 0.0
    print(f"schema/format valid: {ok_n}/{len(rows)} ({rate:.1%})")

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps({"valid_rate": rate, "rows": report}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    raise SystemExit(0 if ok_n == len(rows) else 1)


if __name__ == "__main__":
    main()
