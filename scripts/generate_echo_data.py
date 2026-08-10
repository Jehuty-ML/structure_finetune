#!/usr/bin/env python3
"""用模板合成 Echo 训练数据，校验后划分 train/val。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from structured_llm.contract import validate_turn
from structured_llm.data.generate_echo import generate_dataset, split_train_val


def _write_json(path: Path, rows: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # 训练用字段：去掉 meta 也可保留；保留便于分析
    path.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=300, help="总条数（划分前）")
    parser.add_argument("--seed", type=int, default=3407)
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument(
        "--out-dir",
        default=str(ROOT / "examples" / "echo" / "sample_data"),
    )
    parser.add_argument(
        "--schema",
        default=str(ROOT / "schemas" / "echo_turn.schema.json"),
    )
    args = parser.parse_args()

    rows = generate_dataset(args.count, seed=args.seed)
    bad = 0
    for row in rows:
        vr = validate_turn(
            row["output"], schema_path=args.schema, input_obj=row.get("input")
        )
        if not vr.ok:
            bad += 1
            print(f"失败 {row['id']}: {vr.errors}")
    if bad:
        raise SystemExit(f"合成数据校验失败：{bad}/{len(rows)}")

    train, val = split_train_val(rows, val_ratio=args.val_ratio, seed=args.seed)
    out_dir = Path(args.out_dir)
    _write_json(out_dir / "train.json", train)
    _write_json(out_dir / "val.json", val)
    print(f"已写入 train={len(train)} val={len(val)} -> {out_dir}")
    print("全部通过契约校验。")


if __name__ == "__main__":
    main()
