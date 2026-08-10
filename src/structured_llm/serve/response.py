"""解析生成文本 → VoiceTurn；假 TTS 通道。"""

from __future__ import annotations

from typing import Any, Optional

from structured_llm.contract import validate_turn


def parse_generation_to_response(
    text: str,
    schema_path: str = "schemas/echo_turn.schema.json",
    input_obj: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """与训练门禁 / 评测共用 validate_turn。"""
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
