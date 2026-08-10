from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from structured_llm.contract import validate_turn
from structured_llm.data import format_user_message, load_json


@dataclass
class CaseResult:
    case_id: str
    name: str
    passed: bool
    detail: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)


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
    return problems


def evaluate_suite(
    cases_path: str | Path,
    schema_path: str | Path,
    mode: str = "fixture",
    generate_fn=None,
) -> dict[str, Any]:
    """
    mode=fixture：使用用例文件中的 fixture_output（CI / 无 GPU）。
    mode=generate：调用 generate_fn(system_prompt, user_message) -> str。
    """
    suite = load_json(cases_path)
    schema = load_json(schema_path)
    system_prompt = ""
    sp = suite.get("system_prompt_path")
    if sp:
        system_prompt = Path(sp).read_text(encoding="utf-8").strip()

    results: list[CaseResult] = []
    format_ok = 0
    schema_ok = 0
    total = 0

    for case in suite.get("cases", []):
        check_type = case.get("check_type", "contract")
        if check_type == "multi_turn":
            results.append(
                _eval_multi_turn(case, schema, system_prompt, mode, generate_fn)
            )
            total += 1
            if results[-1].passed:
                format_ok += 1
                schema_ok += 1
            continue

        total += 1
        output = _resolve_output(case, case.get("input"), [], system_prompt, mode, generate_fn)
        vr = validate_turn(output, schema=schema)
        if vr.ok:
            format_ok += 1
            schema_ok += 1
        expect_problems = []
        if vr.ok and case.get("expect") and vr.parsed:
            expect_problems = _check_expectations(vr.parsed.payload, case["expect"])
        passed = vr.ok and not expect_problems
        detail = "; ".join(vr.errors + expect_problems) if not passed else "通过"
        results.append(
            CaseResult(
                case_id=case.get("id", ""),
                name=case.get("name", ""),
                passed=passed,
                detail=detail,
                metrics={"format_ok": vr.ok, "warnings": vr.warnings},
            )
        )

    passed_n = sum(1 for r in results if r.passed)
    return {
        "total": total,
        "passed": passed_n,
        "format_valid_rate": format_ok / total if total else 0.0,
        "schema_valid_rate": schema_ok / total if total else 0.0,
        "pass_rate": passed_n / total if total else 0.0,
        "results": [r.__dict__ for r in results],
    }


def _resolve_output(
    case: dict[str, Any],
    input_obj: Any,
    abstracts: list[str],
    system_prompt: str,
    mode: str,
    generate_fn,
) -> str:
    if mode == "fixture":
        if "fixture_output" in case:
            return case["fixture_output"]
        # 多轮时 fixture_output 在各 round 上
        raise ValueError(f"用例 {case.get('id')} 缺少 fixture_output")
    if generate_fn is None:
        raise ValueError("mode=generate 时必须提供 generate_fn")
    user_message = format_user_message(input_obj, abstracts)
    return generate_fn(system_prompt, user_message)


def _eval_multi_turn(
    case: dict[str, Any],
    schema: dict[str, Any],
    system_prompt: str,
    mode: str,
    generate_fn,
) -> CaseResult:
    abstracts: list[str] = []
    problems: list[str] = []
    for i, round_data in enumerate(case.get("rounds", []), start=1):
        output = round_data.get("fixture_output") if mode == "fixture" else None
        if mode == "generate":
            output = _resolve_output(
                round_data, round_data["user"], abstracts, system_prompt, mode, generate_fn
            )
        assert output is not None
        vr = validate_turn(output, schema=schema)
        if not vr.ok:
            problems.append(f"第 {i} 轮：" + "; ".join(vr.errors))
            break
        assert vr.parsed is not None
        mentions = round_data.get("expect_abstract_mentions_any")
        if mentions:
            abs_l = vr.parsed.abstract.lower()
            if not any(m.lower() in abs_l for m in mentions):
                problems.append(
                    f"第 {i} 轮：abstract 未包含任一关键词 {mentions}：{vr.parsed.abstract!r}"
                )
        abstracts.append(vr.parsed.abstract)

    passed = len(problems) == 0
    return CaseResult(
        case_id=case.get("id", ""),
        name=case.get("name", ""),
        passed=passed,
        detail="通过" if passed else "; ".join(problems),
    )
