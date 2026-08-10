#!/usr/bin/env python3
"""运行 Echo 契约评测套件（默认 fixture 模式）。"""

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
        help="评测用例 JSON 路径",
    )
    parser.add_argument(
        "--schema",
        default=str(ROOT / "schemas" / "echo_turn.schema.json"),
        help="JSON Schema 路径",
    )
    parser.add_argument(
        "--mode",
        choices=("fixture", "generate"),
        default="fixture",
        help="fixture=使用金标输出；generate=需接入 generate_fn",
    )
    parser.add_argument("--json-out", default="", help="可选：报告输出路径")
    args = parser.parse_args()

    if args.mode == "generate":
        print(
            "mode=generate 是推理栈接入钩子。"
            "在接入 generate_fn 之前请使用 fixture 模式。",
            file=sys.stderr,
        )
        raise SystemExit(2)

    summary = evaluate_suite(args.cases, args.schema, mode=args.mode)
    print(
        f"通过率={summary['pass_rate']:.1%} "
        f"格式合法率={summary['format_valid_rate']:.1%} "
        f"({summary['passed']}/{summary['total']})"
    )
    for r in summary["results"]:
        status = "通过" if r["passed"] else "失败"
        print(f"  [{status}] {r['case_id']}: {r['detail']}")

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    raise SystemExit(0 if summary["passed"] == summary["total"] else 1)


if __name__ == "__main__":
    main()
