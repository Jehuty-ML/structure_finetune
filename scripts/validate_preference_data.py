#!/usr/bin/env python3
"""校验 DPO 偏好数据：chosen 必过契约；rejected 可选。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from structured_llm.contract import validate_quest_turn, validate_turn
from structured_llm.data import iter_dpo_rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, help="偏好 JSON：{input,chosen,rejected}")
    parser.add_argument(
        "--contract",
        choices=("echo", "quest"),
        default="echo",
    )
    parser.add_argument(
        "--schema",
        default=str(ROOT / "schemas" / "echo_turn.schema.json"),
    )
    parser.add_argument(
        "--require-rejected-valid",
        action="store_true",
        help="若设置，则 rejected 也必须过契约（仅风格对时有用）",
    )
    parser.add_argument("--json-out", default="")
    args = parser.parse_args()

    rows = list(iter_dpo_rows(args.data))
    report = []
    ok_n = 0
    for row in rows:
        inp = row["input"] if isinstance(row.get("input"), dict) else None
        chosen = str(row["chosen"])
        rejected = str(row["rejected"])
        errors: list[str] = []
        if not chosen.strip() or not rejected.strip():
            errors.append("empty chosen/rejected")
        if chosen == rejected:
            errors.append("chosen == rejected")
        if args.contract == "quest":
            cr = validate_quest_turn(chosen, input_obj=inp)
        else:
            cr = validate_turn(chosen, schema_path=args.schema, input_obj=inp)
        if not cr.ok:
            errors.extend([f"chosen:{e}" for e in cr.errors])
        rejected_ok = None
        if args.require_rejected_valid:
            if args.contract == "quest":
                rr = validate_quest_turn(rejected, input_obj=inp)
            else:
                rr = validate_turn(rejected, schema_path=args.schema, input_obj=inp)
            rejected_ok = rr.ok
            if not rr.ok:
                errors.extend([f"rejected:{e}" for e in rr.errors])
        ok = not errors
        if ok:
            ok_n += 1
        else:
            print(f"失败 {row.get('id')}: {errors}")
        report.append(
            {
                "id": row.get("id"),
                "ok": ok,
                "errors": errors,
                "pair_type": (row.get("meta") or {}).get("pair_type"),
                "rejected_valid": rejected_ok,
            }
        )

    rate = ok_n / len(rows) if rows else 0.0
    print(f"偏好合法：{ok_n}/{len(rows)} ({rate:.1%})")
    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps({"valid_rate": rate, "rows": report}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    raise SystemExit(0 if ok_n == len(rows) else 1)


if __name__ == "__main__":
    main()
