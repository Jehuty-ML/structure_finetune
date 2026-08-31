"""解析生成文本 → 契约字段；假下游通道（TTS / 引擎）。"""

from __future__ import annotations

from typing import Any, Optional

from structured_llm.contract import validate_quest_turn, validate_turn


def parse_generation_to_response(
    text: str,
    schema_path: str = "schemas/echo_turn.schema.json",
    input_obj: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Echo：与训练门禁 / 评测共用 validate_turn。"""
    result = validate_turn(
        text, schema_path=schema_path, input_obj=input_obj
    )
    if not result.ok or result.parsed is None:
        return {"ok": False, "errors": result.errors, "raw": text}
    p = result.parsed
    return {
        "ok": True,
        "think": p.think,
        "voice": p.payload,
        "warnings": result.warnings,
    }


def parse_quest_generation_to_response(
    text: str,
    input_obj: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Quest：与训练门禁共用 validate_quest_turn。"""
    result = validate_quest_turn(text, input_obj=input_obj)
    if not result.ok or result.parsed is None:
        return {
            "ok": False,
            "errors": result.errors,
            "warnings": result.warnings,
            "raw": text,
        }
    p = result.parsed
    say = _scrub_quest_jargon(p.say)
    abstract = _scrub_quest_jargon(p.abstract)
    warnings = list(result.warnings)
    if say != p.say or abstract != p.abstract:
        warnings.append("scrub: 已去掉「交换后」等训练套话")
    return {
        "ok": True,
        "think": p.think,
        "state": dict(p.state),
        "say": say,
        "cmd": dict(p.cmd),
        "stats": dict(p.stats),
        "abstract": abstract,
        "warnings": warnings,
    }


def _scrub_quest_jargon(text: str) -> str:
    """去掉易泄漏到玩家旁白的训练元话术。"""
    if not text:
        return text
    out = text
    for bad, good in (
        ("交换后，", ""),
        ("交换后", ""),
        ("交换结束，", ""),
        ("交换结束", ""),
        ("攻防四拍完成；", ""),
        ("攻防四拍完成", ""),
        ("攻防四拍已完成；", ""),
        ("攻防四拍已完成", ""),
        ("攻防四拍完整；", ""),
        ("攻防四拍完整", ""),
        ("攻防四拍结束，", ""),
        ("攻防四拍结束", ""),
        ("攻防四拍完；", ""),
        ("攻防四拍完", ""),
        ("攻防四拍；", ""),
        ("攻防四拍", ""),
        ("four rounds", ""),
        ("攻防交换完毕；", ""),
        ("攻击交换完毕；", ""),
        ("攻防交换完毕", ""),
        ("攻击交换完毕", ""),
        ("显式全交换", ""),
        ("全交换", ""),
        ("交换完成", ""),
        ("交换战场", "换了地点"),
        ("交换", ""),
        ("回操作菜单。", "请选择攻击、技能、道具或逃跑。"),
        ("请回操作菜单。", "请选择攻击、技能、道具或逃跑。"),
        ("回探索菜单。", ""),
        ("或回探索菜单", ""),
    ):
        out = out.replace(bad, good)
    while "  " in out:
        out = out.replace("  ", " ")
    out = out.replace("，，", "，").replace("。。", "。").replace("；；", "；")
    return out.strip("；， ").strip()


def fake_tts_consume(
    voice: dict[str, Any], *, as_log_line: bool = False
) -> dict[str, Any] | str:
    """假 TTS：只取口播通道字段。"""
    payload = {
        "utter": voice.get("utter"),
        "emotion": voice.get("emotion"),
        "volume": voice.get("volume"),
        "pace": voice.get("pace"),
        "should_speak": voice.get("should_speak"),
    }
    if as_log_line:
        if not payload.get("should_speak"):
            return (
                f"[fake-tts] skip speak | on-screen text={payload.get('utter')!r}"
            )
        return (
            f"[fake-tts] speak utter={payload.get('utter')!r} "
            f"emotion={payload.get('emotion')} "
            f"volume={payload.get('volume')} pace={payload.get('pace')}"
        )
    return payload


def fake_engine_consume(
    *,
    state: dict[str, Any],
    say: str,
    cmd: dict[str, Any],
    stats: dict[str, Any],
    as_log_line: bool = False,
) -> dict[str, Any] | str:
    """假 RPG 引擎：吃 state / say / cmd / stats。"""
    payload = {
        "phase": state.get("phase"),
        "node": state.get("node"),
        "allowed": state.get("allowed"),
        "say": say,
        "action": cmd.get("action"),
        "target": cmd.get("target"),
        "end_turn": cmd.get("end_turn"),
        "hp": stats.get("hp"),
        "mp": stats.get("mp"),
        "loc": stats.get("loc"),
        "quest": stats.get("quest"),
    }
    if as_log_line:
        return (
            f"[fake-engine] phase={payload['phase']} node={payload['node']} "
            f"action={payload['action']} end_turn={payload['end_turn']} "
            f"say={payload['say']!r}"
        )
    return payload
