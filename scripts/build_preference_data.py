#!/usr/bin/env python3
"""从 SFT JSON 合成 DPO 偏好对（chosen=原 output，rejected=损坏/错配）。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from structured_llm.data import (
    build_preference_pairs,
    iter_sft_rows,
    save_json,
    split_train_val,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sft-data",
        required=True,
        help="SFT JSON（含 input/output）",
    )
    parser.add_argument(
        "--out-dir",
        required=True,
        help="输出目录（写入 train.json / val.json）",
    )
    parser.add_argument(
        "--contract",
        choices=("echo", "quest"),
        default="echo",
    )
    parser.add_argument("--seed", type=int, default=3407)
    parser.add_argument(
        "--pairs-per-row",
        type=int,
        default=2,
        help="每条 SFT 合成多少偏好对",
    )
    parser.add_argument(
        "--pair-types",
        default="format,style,cross",
        help="逗号分隔：format|style|cross",
    )
    parser.add_argument(
        "--val-ratio",
        type=float,
        default=0.1,
        help="验证集比例",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="最多取前 N 条 SFT（0=全部）",
    )
    args = parser.parse_args()

    rows = list(iter_sft_rows(args.sft_data))
    if args.limit and args.limit > 0:
        rows = rows[: args.limit]
    types = [t.strip() for t in args.pair_types.split(",") if t.strip()]
    pairs = build_preference_pairs(
        rows,
        contract=args.contract,
        seed=args.seed,
        pairs_per_row=args.pairs_per_row,
        pair_types=types,
    )
    train, val = split_train_val(pairs, val_ratio=args.val_ratio, seed=args.seed)
    out = Path(args.out_dir)
    save_json(out / "train.json", train)
    save_json(out / "val.json", val)
    print(
        f"合成偏好对 {len(pairs)} "
        f"(train={len(train)}, val={len(val)}) -> {out}"
    )


if __name__ == "__main__":
    main()
