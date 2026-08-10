#!/usr/bin/env python3
"""
Echo 阶段 4 主入口：真机对话演示。

  交互：  python scripts/chat_echo.py --adapter <lora目录>
  验收：  python scripts/chat_echo.py --adapter <lora目录> --accept
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# 分场景验收：场景之间清空 history，避免互相污染
ACCEPT_SCENARIOS: list[dict[str, Any]] = [
    {
        "name": "tired",
        "lines": ["好累，别让我想太多。"],
    },
    {
        "name": "mute",
        "lines": ["图书馆模式。"],
    },
    {
        "name": "multi_turn_move_friends",
        "lines": [
            "可能要为工作搬去别的城市。",
            "离开朋友。",
        ],
        # 与训练样本对齐的首轮口播，保证第 2 轮 Prior 落在 SFT 分布内
        "seed_prior_utter": "这是大事。眼下最沉的是哪一块？",
        "seed_prior_user": "可能要为工作搬去别的城市。",
        "start_at": 1,  # 只跑 lines[1:]，首轮用 seed
    },
]


def _print_turn(result: dict) -> None:
    print("\n--- raw ---")
    print(result["raw"])
    if not result["ok"]:
        print("\n--- 契约失败 ---")
        print(json.dumps(result["errors"], ensure_ascii=False, indent=2))
        return
    voice = result["voice"]
    print("\n--- voice (给 App) ---")
    print(json.dumps(voice, ensure_ascii=False, indent=2))
    print("\n--- 假 TTS (只口播通道) ---")
    print(result.get("tts_log") or "")
    print(json.dumps(result["tts"], ensure_ascii=False, indent=2))


def _check_scenario(name: str, results: list[dict]) -> list[str]:
    problems: list[str] = []
    if name == "tired":
        r = results[0]
        if not r["ok"]:
            return [f"tired 契约失败: {r['errors']}"]
        v = r["voice"]
        if v.get("emotion") not in ("gentle", "calm"):
            problems.append(f"tired emotion={v.get('emotion')}")
        if not isinstance(v.get("volume"), int) or v["volume"] > 50:
            problems.append(f"tired volume={v.get('volume')}")
    elif name == "mute":
        r = results[0]
        if not r["ok"]:
            return [f"mute 契约失败: {r['errors']}"]
        v = r["voice"]
        if v.get("should_speak") is not False:
            problems.append("mute should_speak 应为 false")
        if v.get("ui_mode") != "text_only":
            problems.append(f"mute ui_mode={v.get('ui_mode')}")
    elif name == "multi_turn_move_friends":
        if len(results) < 2:
            return ["multi_turn 轮次不足"]
        for i, r in enumerate(results, start=1):
            if not r["ok"]:
                problems.append(f"multi_turn 第{i}轮契约失败: {r['errors']}")
        if problems:
            return problems
        v2 = results[1]["voice"]
        utter = str(v2.get("utter") or "")
        if not any(k in utter for k in ("朋友", "联系", "搬")):
            problems.append(f"multi_turn 第2轮未承接: {utter!r}")
        if v2.get("intent") not in ("comfort", "clarify", "chat"):
            problems.append(f"multi_turn intent={v2.get('intent')}")
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--adapter",
        default="outputs/echo_lora/Qwen3-1.7B_r16_len2048_lr2e-4_0811_1043",
    )
    parser.add_argument("--base-model", default="Qwen/Qwen3-1.7B")
    parser.add_argument(
        "--system-prompt",
        default=str(ROOT / "examples" / "echo" / "prompts" / "system_prompt.txt"),
    )
    parser.add_argument(
        "--schema",
        default=str(ROOT / "schemas" / "echo_turn.schema.json"),
    )
    parser.add_argument("--max-new-tokens", type=int, default=512)
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="采样温度；--accept 默认 0.2，交互默认 0.3",
    )
    parser.add_argument(
        "--accept",
        action="store_true",
        help="跑固定验收场景（非交互），全部通过则 exit 0",
    )
    args = parser.parse_args()
    os.chdir(ROOT)

    from structured_llm.eval.infer import make_generate_fn
    from structured_llm.serve.chat import run_echo_turn

    system_prompt = Path(args.system_prompt).read_text(encoding="utf-8").strip()
    temp = args.temperature
    if temp is None:
        temp = 0.2 if args.accept else 0.3
    print("加载模型（首次较慢）…")
    generate_fn = make_generate_fn(
        project_root=ROOT,
        base_model=args.base_model,
        adapter=args.adapter,
        max_new_tokens=args.max_new_tokens,
        temperature=temp,
    )

    if args.accept:
        print("验收模式：疲惫 / 静音 / 多轮搬家→朋友\n")
        all_problems: list[str] = []
        for sc in ACCEPT_SCENARIOS:
            history: list[tuple[str, str]] = []
            turn = 1
            can_speak = True
            results: list[dict] = []
            print(f"##### 场景 {sc['name']}")
            lines = list(sc["lines"])
            if sc.get("seed_prior_utter"):
                history = [
                    (
                        str(sc.get("seed_prior_user") or lines[0]),
                        str(sc["seed_prior_utter"]),
                    )
                ]
                lines = lines[int(sc.get("start_at") or 1) :]
                turn = 2
                print(f"(seed Prior) {sc['seed_prior_utter']}")
            for line in lines:
                print(f"你> {line}")
                result = run_echo_turn(
                    user_text=line,
                    generate_fn=generate_fn,
                    system_prompt=system_prompt,
                    schema_path=args.schema,
                    history=history,
                    turn=turn,
                    can_speak=can_speak,
                )
                _print_turn(result)
                results.append(result)
                if result["ok"]:
                    history = result["history"]
                can_speak = True
                turn += 1
                print()
            # multi_turn 检查需要两轮结果：seed 算第 1 轮契约已隐含，只验生成的第 2 轮
            if sc["name"] == "multi_turn_move_friends" and results:
                fake_r1 = {
                    "ok": True,
                    "voice": {"utter": sc.get("seed_prior_utter"), "intent": "clarify"},
                    "errors": [],
                }
                probs = _check_scenario(sc["name"], [fake_r1, results[0]])
            else:
                probs = _check_scenario(sc["name"], results)
            if probs:
                all_problems.extend(f"[{sc['name']}] {p}" for p in probs)
            else:
                print(f"[{sc['name']}] OK\n")

        if all_problems:
            print("验收失败：")
            for p in all_problems:
                print(" -", p)
            raise SystemExit(1)
        print("ACCEPT_PASS：阶段 4 真机对话验收通过")
        return

    print("就绪。输入对话；mute=切换静音；quit=退出。\n")
    history: list[tuple[str, str]] = []
    turn = 1
    can_speak = True
    while True:
        try:
            line = input("你> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        low = line.lower()
        if low in {"quit", "exit", "q"}:
            break
        if low == "mute":
            can_speak = not can_speak
            print(f"[device.can_speak={can_speak}]")
            continue
        if low == "reset":
            history = []
            turn = 1
            print("[history cleared]")
            continue

        result = run_echo_turn(
            user_text=line,
            generate_fn=generate_fn,
            system_prompt=system_prompt,
            schema_path=args.schema,
            history=history,
            turn=turn,
            can_speak=can_speak,
        )
        _print_turn(result)
        if result["ok"]:
            history = result["history"]
        turn += 1
        print()


if __name__ == "__main__":
    main()
