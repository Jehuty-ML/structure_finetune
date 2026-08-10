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
    return {
        "ok": True,
        "think": p.think,
        "state": dict(p.state),
        "say": p.say,
        "cmd": dict(p.cmd),
        "stats": dict(p.stats),
        "abstract": p.abstract,
        "warnings": result.warnings,
    }


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
