#!/usr/bin/env python3
"""
Quest 真机对话：生成 → validate_quest_turn → 假引擎字段。

  交互：  python scripts/chat_quest.py --adapter <lora目录>
  验收：  python scripts/chat_quest.py --adapter <lora目录> --accept
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

# 分场景验收：每场景独立 fsm/stats，互不清空污染
ACCEPT_SCENARIOS: list[dict[str, Any]] = [
    {
        "name": "explore_fork",
        "lines": ["我往前走。"],
        "fsm": {"phase": "explore", "node": "forest_fork"},
        "stats": {
            "hp": "80",
            "mp": "20",
            "loc": "森林路口",
            "quest": "找药草",
        },
        "expect": {
            "phase": "explore",
            "action_any": ["prompt_choice", "move"],
        },
    },
    {
        "name": "combat_start",
        "lines": ["有怪物！"],
        "fsm": {"phase": "explore", "node": "cave_mouth"},
        "stats": {
            "hp": "76",
            "mp": "18",
            "loc": "洞穴入口",
            "quest": "找药草",
        },
        "expect": {
            "phase": "combat",
            "action_any": ["prompt_choice", "attack"],
        },
    },
    {
        "name": "flee",
        "lines": ["我跑！"],
        "fsm": {"phase": "combat", "node": "round_player"},
        "stats": {
            "hp": "70",
            "mp": "15",
            "loc": "洞穴入口",
            "quest": "找药草",
        },
        "expect": {
            "phase": "explore",
            "action": "flee",
            "end_turn": "1",
        },
    },
]


def _print_turn(result: dict) -> None:
    print("\n--- raw ---")
    print(result["raw"])
    if not result["ok"]:
        print("\n--- 契约失败 ---")
        print(json.dumps(result["errors"], ensure_ascii=False, indent=2))
        return
    print("\n--- state / cmd / stats (给引擎) ---")
    print(
        json.dumps(
            {
                "state": result.get("state"),
                "cmd": result.get("cmd"),
                "stats": result.get("stats"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    print("\n--- say (给玩家) ---")
    print(result.get("say") or "")
    print("\n--- abstract ---")
    print(result.get("abstract") or "")
    print("\n--- 假引擎 ---")
    print(result.get("engine_log") or "")
    print(json.dumps(result.get("engine"), ensure_ascii=False, indent=2))


def _check_scenario(name: str, results: list[dict], expect: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    if not results:
        return [f"{name} 无结果"]
    r = results[0]
    if not r["ok"]:
        return [f"{name} 契约失败: {r['errors']}"]
    state = r.get("state") or {}
    cmd = r.get("cmd") or {}
    if "phase" in expect and state.get("phase") != expect["phase"]:
        problems.append(f"phase={state.get('phase')} != {expect['phase']}")
    if "action" in expect and cmd.get("action") != expect["action"]:
        problems.append(f"action={cmd.get('action')} != {expect['action']}")
    if "action_any" in expect and cmd.get("action") not in expect["action_any"]:
        problems.append(
            f"action={cmd.get('action')} 不在 {expect['action_any']} 中"
        )
    if "end_turn" in expect and str(cmd.get("end_turn")) != str(expect["end_turn"]):
        problems.append(f"end_turn={cmd.get('end_turn')} != {expect['end_turn']}")
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--adapter",
        default="",
        help="LoRA 目录；空则仅基座（Prompt-only）",
    )
    parser.add_argument("--base-model", default="Qwen/Qwen3-1.7B")
    parser.add_argument(
        "--system-prompt",
        default=str(ROOT / "examples" / "quest" / "prompts" / "system_prompt.txt"),
    )
    parser.add_argument("--max-new-tokens", type=int, default=768)
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
    from structured_llm.serve.chat import run_quest_turn

    system_prompt = Path(args.system_prompt).read_text(encoding="utf-8").strip()
    temp = args.temperature
    if temp is None:
        temp = 0.2 if args.accept else 0.3
    print("加载模型（首次较慢）…")
    generate_fn = make_generate_fn(
        project_root=ROOT,
        base_model=args.base_model,
        adapter=args.adapter or None,
        max_new_tokens=args.max_new_tokens,
        temperature=temp,
    )

    if args.accept:
        print("验收模式：探索路口 / 遇敌 / 逃跑\n")
        all_problems: list[str] = []
        for sc in ACCEPT_SCENARIOS:
            history: list[tuple[str, str]] = []
            fsm = dict(sc["fsm"])
            stats = dict(sc["stats"])
            results: list[dict] = []
            print(f"##### 场景 {sc['name']}  fsm={fsm}")
            for line in sc["lines"]:
                print(f"你> {line}")
                result = run_quest_turn(
                    user_text=line,
                    generate_fn=generate_fn,
                    system_prompt=system_prompt,
                    fsm=fsm,
                    stats=stats,
                    history=history,
                )
                _print_turn(result)
                results.append(result)
                if result["ok"]:
                    history = result["history"]
                    fsm = result["fsm"]
                    stats = result["session_stats"]
                print()
            probs = _check_scenario(sc["name"], results, sc.get("expect") or {})
            if probs:
                all_problems.extend(f"[{sc['name']}] {p}" for p in probs)
            else:
                print(f"[{sc['name']}] OK\n")

        if all_problems:
            print("验收失败：")
            for p in all_problems:
                print(" -", p)
            raise SystemExit(1)
        print("ACCEPT_PASS：Quest 真机对话验收通过")
        return

    print("就绪。输入行动；status=看会话；reset=重置；quit=退出。\n")
    history: list[tuple[str, str]] = []
    fsm = {"phase": "explore", "node": "forest_fork"}
    stats = {
        "hp": "80",
        "mp": "20",
        "loc": "森林路口",
        "quest": "找药草",
    }
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
        if low == "status":
            print(json.dumps({"fsm": fsm, "stats": stats}, ensure_ascii=False, indent=2))
            continue
        if low == "reset":
            history = []
            fsm = {"phase": "explore", "node": "forest_fork"}
            stats = {
                "hp": "80",
                "mp": "20",
                "loc": "森林路口",
                "quest": "找药草",
            }
            print("[session cleared]")
            continue

        result = run_quest_turn(
            user_text=line,
            generate_fn=generate_fn,
            system_prompt=system_prompt,
            fsm=fsm,
            stats=stats,
            history=history,
        )
        _print_turn(result)
        if result["ok"]:
            history = result["history"]
            fsm = result["fsm"]
            stats = result["session_stats"]
        print()


if __name__ == "__main__":
    main()
