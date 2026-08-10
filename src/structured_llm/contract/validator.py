from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .parser import ParsedTurn, try_parse_turn

_TAG_IN_UTTER = re.compile(
    r"</?(?:think|state|abstract)\b|\[/?json\]", re.I
)
_STAGE_DIR = re.compile(r"[（(][^）)]{1,40}[）)]")

UTTER_WARN_CHARS = 80


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    parsed: Optional[ParsedTurn] = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "errors": self.errors,
            "warnings": self.warnings,
            "parsed": None
            if self.parsed is None
            else {
                "think": self.parsed.think,
                "payload": self.parsed.payload,
            },
        }


def _load_schema(schema_path: Path) -> dict[str, Any]:
    with schema_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _validate_against_schema(
    payload: dict[str, Any], schema: dict[str, Any]
) -> list[str]:
    """对 Echo 回合 JSON 做 Schema 检查；优先 jsonschema。"""
    try:
        import jsonschema

        validator = jsonschema.Draft202012Validator(schema)
        return [e.message for e in sorted(validator.iter_errors(payload), key=str)]
    except ImportError:
        errors: list[str] = []
        for key in schema.get("required", []):
            if key not in payload:
                errors.append(f"缺少必填字段：{key}")
        props = schema.get("properties", {})
        if "utter" in payload and not isinstance(payload["utter"], str):
            errors.append("utter 必须是字符串")
        if "volume" in payload:
            vol = payload["volume"]
            if not isinstance(vol, int) or isinstance(vol, bool) or not (0 <= vol <= 100):
                errors.append("volume 必须是 [0, 100] 的整数")
        for enum_key in ("emotion", "pace", "intent", "ui_mode"):
            if enum_key in payload and enum_key in props:
                enum = props[enum_key].get("enum")
                if enum and payload[enum_key] not in enum:
                    errors.append(f"{enum_key} 必须是以下之一：{enum}")
        for bool_key in ("should_speak", "end_turn"):
            if bool_key in payload and not isinstance(payload[bool_key], bool):
                errors.append(f"{bool_key} 必须是布尔值")
        return errors


def validate_turn(
    text: str,
    schema: Optional[dict[str, Any]] = None,
    schema_path: Optional[str | Path] = None,
    strict_tts: bool = True,
    input_obj: Optional[dict[str, Any]] = None,
) -> ValidationResult:
    """校验多块回合；提供 input_obj 时额外检查静音一致性。"""
    parsed, parse_error = try_parse_turn(text)
    if parse_error:
        return ValidationResult(ok=False, errors=[parse_error])

    assert parsed is not None
    errors: list[str] = []
    warnings: list[str] = []

    if schema is None and schema_path is not None:
        schema = _load_schema(Path(schema_path))
    if schema is not None:
        errors.extend(_validate_against_schema(parsed.payload, schema))

    utter = parsed.payload.get("utter", "")
    if isinstance(utter, str):
        if _TAG_IN_UTTER.search(utter):
            errors.append("utter 不得包含结构标签")
        if strict_tts and _STAGE_DIR.search(utter):
            errors.append("utter 含括号演技注释（对 TTS 不安全）")
        if len(utter) > UTTER_WARN_CHARS:
            warnings.append(f"utter 过长（>{UTTER_WARN_CHARS} 字），口播宜短")

    if not parsed.think:
        warnings.append("think 为空")

    if isinstance(input_obj, dict):
        device = input_obj.get("device") or {}
        if device.get("can_speak") is False:
            if parsed.payload.get("should_speak") is True:
                errors.append("device.can_speak=false 时 should_speak 必须为 false")
            if parsed.payload.get("ui_mode") not in (None, "text_only"):
                errors.append("device.can_speak=false 时 ui_mode 必须为 text_only")

    return ValidationResult(
        ok=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        parsed=parsed,
    )
