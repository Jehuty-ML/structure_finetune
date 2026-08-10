#!/usr/bin/env python3
"""合成 Quest RPG 训练数据并校验。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from structured_llm.contract.quest_validator import validate_quest_turn
from structured_llm.data.generate_quest import generate_dataset, split_train_val


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=200)
    parser.add_argument("--seed", type=int, default=3407)
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument(
        "--out-dir",
        default=str(ROOT / "examples" / "quest" / "sample_data"),
    )
    args = parser.parse_args()

    rows = generate_dataset(args.count, seed=args.seed)
    bad = 0
    for row in rows:
        vr = validate_quest_turn(row["output"], input_obj=row.get("input"))
        if not vr.ok:
            bad += 1
            print(f"失败 {row['id']}: {vr.errors}")
    if bad:
        raise SystemExit(f"合成数据校验失败：{bad}/{len(rows)}")

    train, val = split_train_val(rows, val_ratio=args.val_ratio, seed=args.seed)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "train.json").write_text(
        json.dumps(train, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (out / "val.json").write_text(
        json.dumps(val, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    sample = train[:5]
    (out / "train_sample.json").write_text(
        json.dumps(sample, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"已写入 train={len(train)} val={len(val)} sample={len(sample)} -> {out}")


if __name__ == "__main__":
    main()
