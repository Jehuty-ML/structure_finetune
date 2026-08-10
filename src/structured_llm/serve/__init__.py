"""可选的 FastAPI 服务辅助：返回解析后的 VoiceTurn 对象。"""

from __future__ import annotations

from typing import Any

from structured_llm.contract import validate_turn


def parse_generation_to_response(
    text: str, schema_path: str = "schemas/echo_turn.schema.json"
) -> dict[str, Any]:
    result = validate_turn(text, schema_path=schema_path)
    if not result.ok or result.parsed is None:
        return {"ok": False, "errors": result.errors, "raw": text}
    p = result.parsed
    return {
        "ok": True,
        "think": p.think,
        "state": p.state,
        "voice": p.payload,
        "abstract": p.abstract,
        "warnings": result.warnings,
    }
