#!/usr/bin/env python3
"""运行契约评测：fixture 或 generate（基座 / LoRA 对比）。支持 echo | quest。"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.chdir(ROOT)

from structured_llm.eval import evaluate_suite


def _print_summary(label: str, summary: dict) -> None:
    channel = "say安全" if summary.get("contract") == "quest" else "TTS安全"
    print(
        f"[{label}] 通过率={summary['pass_rate']:.1%} "
        f"格式={summary['format_valid_rate']:.1%} "
        f"Schema={summary['schema_valid_rate']:.1%} "
        f"{channel}={summary.get('tts_safe_rate', 0):.1%} "
        f"({summary['passed']}/{summary['total']})"
    )
    for r in summary["results"]:
        status = "通过" if r["passed"] else "失败"
        print(f"  [{status}] {r['case_id']}: {r['detail']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--contract",
        choices=("echo", "quest"),
        default="echo",
        help="契约类型",
    )
    parser.add_argument(
        "--cases",
        default="",
        help="评测用例；默认随 --contract 选择 echo/quest",
    )
    parser.add_argument(
        "--schema",
        default=str(ROOT / "schemas" / "echo_turn.schema.json"),
        help="Echo JSON Schema（仅 --contract echo）",
    )
    parser.add_argument(
        "--mode",
        choices=("fixture", "generate"),
        default="fixture",
    )
    parser.add_argument(
        "--base-model",
        default="Qwen/Qwen3-1.7B",
        help="基座模型 ID 或本地路径（generate 模式）",
    )
    parser.add_argument(
        "--adapter",
        default="",
        help="LoRA 目录；与 --compare 联用时作为 SFT 侧",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="对比 Prompt-only 基座 vs 基座+adapter",
    )
    parser.add_argument("--json-out", default="")
    parser.add_argument("--max-new-tokens", type=int, default=512)
    args = parser.parse_args()

    if not args.cases:
        args.cases = str(
            ROOT
            / "examples"
            / ("quest" if args.contract == "quest" else "echo")
            / "eval_cases.json"
        )

    def _run(mode: str, generate_fn=None) -> dict:
        return evaluate_suite(
            args.cases,
            args.schema if args.contract == "echo" else None,
            mode=mode,
            generate_fn=generate_fn,
            contract=args.contract,
        )

    if args.mode == "fixture":
        summary = _run("fixture")
        _print_summary("fixture", summary)
        if args.json_out:
            Path(args.json_out).write_text(
                json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        raise SystemExit(0 if summary["passed"] == summary["total"] else 1)

    from structured_llm.eval.infer import make_generate_fn

    if args.compare:
        if not args.adapter:
            print("--compare 需要同时提供 --adapter", file=sys.stderr)
            raise SystemExit(2)

        import gc

        import torch

        print("=== Prompt-only 基座 ===")
        base_fn = make_generate_fn(
            project_root=ROOT,
            base_model=args.base_model,
            adapter=None,
            max_new_tokens=args.max_new_tokens,
        )
        base_sum = _run("generate", generate_fn=base_fn)
        _print_summary("base", base_sum)
        del base_fn
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        print("=== 基座 + LoRA ===")
        sft_fn = make_generate_fn(
            project_root=ROOT,
            base_model=args.base_model,
            adapter=args.adapter,
            max_new_tokens=args.max_new_tokens,
        )
        sft_sum = _run("generate", generate_fn=sft_fn)
        _print_summary("sft", sft_sum)

        print("\n对比摘要")
        print(
            f"  基座  通过率={base_sum['pass_rate']:.1%}  "
            f"格式={base_sum['format_valid_rate']:.1%}"
        )
        print(
            f"  SFT   通过率={sft_sum['pass_rate']:.1%}  "
            f"格式={sft_sum['format_valid_rate']:.1%}"
        )
        report = {"base": base_sum, "sft": sft_sum}
        if args.json_out:
            Path(args.json_out).write_text(
                json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        raise SystemExit(0)

    adapter = args.adapter or None
    gen = make_generate_fn(
        project_root=ROOT,
        base_model=args.base_model,
        adapter=adapter,
        max_new_tokens=args.max_new_tokens,
    )
    label = "sft" if adapter else "base"
    summary = _run("generate", generate_fn=gen)
    _print_summary(label, summary)
    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    raise SystemExit(0 if summary["passed"] == summary["total"] else 1)


if __name__ == "__main__":
    main()
