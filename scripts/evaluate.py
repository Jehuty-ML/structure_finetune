#!/usr/bin/env python3
"""Run the Echo contract eval suite (fixture mode by default)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from structured_llm.eval import evaluate_suite


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cases",
        default=str(ROOT / "examples" / "echo" / "eval_cases.json"),
    )
    parser.add_argument(
        "--schema",
        default=str(ROOT / "schemas" / "echo_turn.schema.json"),
    )
    parser.add_argument(
        "--mode",
        choices=("fixture", "generate"),
        default="fixture",
        help="fixture=use golden outputs; generate=requires a wired generate_fn",
    )
    parser.add_argument("--json-out", default="")
    args = parser.parse_args()

    if args.mode == "generate":
        print(
            "mode=generate is a hook for your inference stack. "
            "Use fixture mode until generate_fn is wired.",
            file=sys.stderr,
        )
        raise SystemExit(2)

    summary = evaluate_suite(args.cases, args.schema, mode=args.mode)
    print(
        f"pass_rate={summary['pass_rate']:.1%} "
        f"format_valid_rate={summary['format_valid_rate']:.1%} "
        f"({summary['passed']}/{summary['total']})"
    )
    for r in summary["results"]:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"  [{status}] {r['case_id']}: {r['detail']}")

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    raise SystemExit(0 if summary["passed"] == summary["total"] else 1)


if __name__ == "__main__":
    main()
