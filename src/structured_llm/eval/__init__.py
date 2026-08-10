from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from structured_llm.contract import validate_quest_turn, validate_turn
from structured_llm.data import format_user_message, load_json


@dataclass
class CaseResult:
    case_id: str
    name: str
    passed: bool
    detail: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)
    raw_output: str = ""


def _check_expectations(payload: dict[str, Any], expect: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    if "should_speak" in expect and payload.get("should_speak") != expect["should_speak"]:
        problems.append(
            f"should_speak={payload.get('should_speak')} != {expect['should_speak']}"
        )
    if "volume_max" in expect:
        vol = payload.get("volume")
        if not isinstance(vol, int) or vol > expect["volume_max"]:
            problems.append(f"volume {vol} 超过上限 {expect['volume_max']}")
    if "emotions_any" in expect:
        if payload.get("emotion") not in expect["emotions_any"]:
            problems.append(
                f"emotion {payload.get('emotion')} 不在 {expect['emotions_any']} 中"
            )
    if "pace_any" in expect:
        if payload.get("pace") not in expect["pace_any"]:
            problems.append(f"pace {payload.get('pace')} 不在 {expect['pace_any']} 中")
    if "intent_any" in expect:
        if payload.get("intent") not in expect["intent_any"]:
            problems.append(
                f"intent {payload.get('intent')} 不在 {expect['intent_any']} 中"
            )
    if "utter_mentions_any" in expect:
        utter = str(payload.get("utter") or "")
        keys = expect["utter_mentions_any"]
        if not any(m in utter for m in keys):
            problems.append(f"utter 未包含任一关键词 {keys}：{utter!r}")
    return problems


def _check_quest_expectations(
    *,
    state: dict[str, Any],
    cmd: dict[str, Any],
    say: str,
    expect: dict[str, Any],
) -> list[str]:
    problems: list[str] = []
    if "phase" in expect and state.get("phase") != expect["phase"]:
        problems.append(f"phase={state.get('phase')} != {expect['phase']}")
    if "node" in expect and state.get("node") != expect["node"]:
        problems.append(f"node={state.get('node')} != {expect['node']}")
    if "action" in expect and cmd.get("action") != expect["action"]:
        problems.append(f"action={cmd.get('action')} != {expect['action']}")
    if "action_any" in expect and cmd.get("action") not in expect["action_any"]:
        problems.append(
            f"action={cmd.get('action')} 不在 {expect['action_any']} 中"
        )
    if "end_turn" in expect and str(cmd.get("end_turn")) != str(expect["end_turn"]):
        problems.append(f"end_turn={cmd.get('end_turn')} != {expect['end_turn']}")
    if "say_mentions_any" in expect:
        keys = expect["say_mentions_any"]
        if not any(m in say for m in keys):
            problems.append(f"say 未包含任一关键词 {keys}：{say!r}")
    return problems


def _tts_safe(utter: Any) -> bool:
    if not isinstance(utter, str) or not utter:
        return False
    if re.search(r"</?(?:think|state|abstract)\b|\[/?json\]", utter, re.I):
        return False
    if re.search(r"[（(][^）)]{1,40}[）)]", utter):
        return False
    return True


def _say_safe(say: Any) -> bool:
    if not isinstance(say, str) or not say:
        return False
    if re.search(r"</?(?:think|state|say|cmd|stats|abstract)\b", say, re.I):
        return False
    return True


def evaluate_suite(
    cases_path: str | Path,
    schema_path: str | Path | None = None,
    mode: str = "fixture",
    generate_fn=None,
    contract: str = "echo",
) -> dict[str, Any]:
    """
    mode=fixture：使用用例文件中的 fixture_output（CI / 无 GPU）。
    mode=generate：调用 generate_fn(system_prompt, user_message) -> str。
    contract=echo|quest。
    """
    suite = load_json(cases_path)
    contract = str(contract or suite.get("contract") or "echo").lower()
    schema: dict[str, Any] | None = None
    if contract == "echo":
        if schema_path is None:
            schema_path = "schemas/echo_turn.schema.json"
        schema = load_json(schema_path)

    system_prompt = ""
    sp = suite.get("system_prompt_path")
    if sp:
        sp_path = Path(sp)
        if sp_path.exists():
            system_prompt = sp_path.read_text(encoding="utf-8").strip()

    results: list[CaseResult] = []
    format_ok = 0
    schema_ok = 0
    channel_ok = 0
    total = 0
    prior_label = "Abstract" if contract == "quest" else "Prior"

    for case in suite.get("cases", []):
        check_type = case.get("check_type", "contract")
        if check_type == "multi_turn" and contract == "echo":
            assert schema is not None
            cr = _eval_multi_turn(case, schema, system_prompt, mode, generate_fn)
            results.append(cr)
            total += 1
            if cr.metrics.get("format_ok"):
                format_ok += 1
            if cr.metrics.get("schema_ok"):
                schema_ok += 1
            if cr.metrics.get("tts_ok"):
                channel_ok += 1
            continue

        total += 1
        input_obj = case.get("input")
        output = _resolve_output(
            case,
            input_obj,
            [],
            system_prompt,
            mode,
            generate_fn,
            prior_label=prior_label,
        )
        if contract == "quest":
            vr = validate_quest_turn(
                output,
                input_obj=input_obj if isinstance(input_obj, dict) else None,
            )
            say_ok = bool(vr.parsed and _say_safe(vr.parsed.say))
            expect_problems: list[str] = []
            if vr.ok and case.get("expect") and vr.parsed:
                expect_problems = _check_quest_expectations(
                    state=vr.parsed.state,
                    cmd=vr.parsed.cmd,
                    say=vr.parsed.say,
                    expect=case["expect"],
                )
            if vr.ok:
                format_ok += 1
                schema_ok += 1
            if say_ok:
                channel_ok += 1
            passed = vr.ok and not expect_problems and say_ok
            detail = (
                "; ".join(vr.errors + expect_problems)
                if not passed
                else "通过"
            )
            if vr.ok and not say_ok:
                detail = (detail + "; " if detail != "通过" else "") + "say 含非法标签"
            results.append(
                CaseResult(
                    case_id=case.get("id", ""),
                    name=case.get("name", ""),
                    passed=passed,
                    detail=detail if not passed else "通过",
                    metrics={
                        "format_ok": vr.ok,
                        "schema_ok": vr.ok,
                        "tts_ok": say_ok,
                        "say_ok": say_ok,
                        "warnings": vr.warnings,
                    },
                    raw_output=output,
                )
            )
            continue

        assert schema is not None
        vr = validate_turn(
            output,
            schema=schema,
            input_obj=input_obj if isinstance(input_obj, dict) else None,
        )
        if vr.ok:
            format_ok += 1
            schema_ok += 1
        utter_ok = bool(vr.parsed and _tts_safe(vr.parsed.payload.get("utter")))
        if utter_ok:
            channel_ok += 1
        expect_problems = []
        if vr.ok and case.get("expect") and vr.parsed:
            expect_problems = _check_expectations(vr.parsed.payload, case["expect"])
        passed = vr.ok and not expect_problems and utter_ok
        detail = (
            "; ".join(vr.errors + expect_problems)
            if not passed
            else "通过"
        )
        if vr.ok and not utter_ok:
            detail = (detail + "; " if detail != "通过" else "") + "utter 对 TTS 不安全"
        results.append(
            CaseResult(
                case_id=case.get("id", ""),
                name=case.get("name", ""),
                passed=passed,
                detail=detail if not passed else "通过",
                metrics={
                    "format_ok": vr.ok,
                    "schema_ok": vr.ok,
                    "tts_ok": utter_ok,
                    "warnings": vr.warnings,
                },
                raw_output=output,
            )
        )

    passed_n = sum(1 for r in results if r.passed)
    return {
        "total": total,
        "passed": passed_n,
        "format_valid_rate": format_ok / total if total else 0.0,
        "schema_valid_rate": schema_ok / total if total else 0.0,
        "tts_safe_rate": channel_ok / total if total else 0.0,
        "pass_rate": passed_n / total if total else 0.0,
        "contract": contract,
        "results": [r.__dict__ for r in results],
    }


def _resolve_output(
    case: dict[str, Any],
    input_obj: Any,
    prior_utters: list[str],
    system_prompt: str,
    mode: str,
    generate_fn,
    *,
    prior_label: str = "Prior",
) -> str:
    if mode == "fixture":
        if "fixture_output" in case:
            return case["fixture_output"]
        raise ValueError(f"用例 {case.get('id')} 缺少 fixture_output")
    if generate_fn is None:
        raise ValueError("mode=generate 时必须提供 generate_fn")
    user_message = format_user_message(
        input_obj, prior_utters, prior_label=prior_label
    )
    return generate_fn(system_prompt, user_message)


def _eval_multi_turn(
    case: dict[str, Any],
    schema: dict[str, Any],
    system_prompt: str,
    mode: str,
    generate_fn,
) -> CaseResult:
    prior_utters: list[str] = []
    problems: list[str] = []
    last_output = ""
    format_ok = True
    schema_ok = True
    tts_ok = True
    for i, round_data in enumerate(case.get("rounds", []), start=1):
        output = round_data.get("fixture_output") if mode == "fixture" else None
        if mode == "generate":
            output = _resolve_output(
                round_data,
                round_data["user"],
                prior_utters,
                system_prompt,
                mode,
                generate_fn,
            )
        assert output is not None
        last_output = output
        user = round_data.get("user") if isinstance(round_data.get("user"), dict) else None
        vr = validate_turn(output, schema=schema, input_obj=user)
        if not vr.ok:
            format_ok = False
            schema_ok = False
            tts_ok = False
            problems.append(f"第 {i} 轮：" + "; ".join(vr.errors))
            break
        assert vr.parsed is not None
        if not _tts_safe(vr.parsed.payload.get("utter")):
            tts_ok = False
            problems.append(f"第 {i} 轮：utter 对 TTS 不安全")
            break
        expect = round_data.get("expect") or {}
        # 兼容旧字段名
        if "expect_abstract_mentions_any" in round_data and "utter_mentions_any" not in expect:
            expect = {**expect, "utter_mentions_any": round_data["expect_abstract_mentions_any"]}
        expect_problems = _check_expectations(vr.parsed.payload, expect) if expect else []
        if expect_problems:
            problems.extend(f"第 {i} 轮：{p}" for p in expect_problems)
        prior_utters.append(str(vr.parsed.payload.get("utter") or ""))

    passed = len(problems) == 0
    return CaseResult(
        case_id=case.get("id", ""),
        name=case.get("name", ""),
        passed=passed,
        detail="通过" if passed else "; ".join(problems),
        metrics={
            "format_ok": format_ok and passed,
            "schema_ok": schema_ok and passed,
            "tts_ok": tts_ok and passed,
        },
        raw_output=last_output,
    )
