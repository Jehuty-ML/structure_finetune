#!/usr/bin/env python3
"""按规则卡 + 改写库组装 Quest 训练数据（校验 + 按 user_text 留出 val）。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from structured_llm.data.generate_quest import (
    assemble_dataset,
    dataset_stats,
    split_train_val,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--max-per-rule",
        type=int,
        default=None,
        help="每张规则卡最多取多少条 user_text；默认全量",
    )
    parser.add_argument("--seed", type=int, default=3407)
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument(
        "--rules-dir",
        default=str(ROOT / "examples" / "quest" / "rules"),
    )
    parser.add_argument(
        "--rewrites-dir",
        default=str(ROOT / "examples" / "quest" / "rewrites"),
    )
    parser.add_argument(
        "--out-dir",
        default=str(ROOT / "examples" / "quest" / "sample_data"),
    )
    args = parser.parse_args()

    rows = assemble_dataset(
        rules_dir=args.rules_dir,
        rewrites_dir=args.rewrites_dir,
        seed=args.seed,
        max_per_rule=args.max_per_rule,
    )
    stats = dataset_stats(rows)
    print(
        f"组装完成 n={stats['n']} unique_user={stats['unique_user']} "
        f"by_rule={stats['by_rule']}"
    )

    train, val = split_train_val(rows, val_ratio=args.val_ratio, seed=args.seed)
    train_users = {r["input"]["user_text"] for r in train}
    val_users = {r["input"]["user_text"] for r in val}
    leak = train_users & val_users
    if leak:
        raise SystemExit(f"user_text 泄漏到 train/val：{list(leak)[:5]}")

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
    print(
        f"已写入 train={len(train)} val={len(val)} "
        f"(val_users={len(val_users)}) sample={len(sample)} -> {out}"
    )


if __name__ == "__main__":
    main()
