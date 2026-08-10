from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .parser import ParsedTurn, try_parse_turn

_TAG_IN_UTTER = re.compile(r"</?(?:think|state|abstract)\b", re.I)
_STAGE_DIR = re.compile(r"[（(][^）)]{1,40}[）)]")


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
                "state": self.parsed.state,
                "payload": self.parsed.payload,
                "abstract": self.parsed.abstract,
            },
        }


def _load_schema(schema_path: Path) -> dict[str, Any]:
    with schema_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _validate_against_schema(
    payload: dict[str, Any], schema: dict[str, Any]
) -> list[str]:
    """
    对 Echo 回合 JSON 对象做最小 JSON Schema 检查。
    若已安装 jsonschema 则优先使用；否则按 Echo 必填规则校验。
    """
    try:
        import jsonschema

        validator = jsonschema.Draft202012Validator(schema)
        return [e.message for e in sorted(validator.iter_errors(payload), key=str)]
    except ImportError:
        errors: list[str] = []
        required = schema.get("required", [])
        for key in required:
            if key not in payload:
                errors.append(f"缺少必填字段：{key}")

        props = schema.get("properties", {})
        if "utter" in payload and not isinstance(payload["utter"], str):
            errors.append("utter 必须是字符串")
        if "volume" in payload:
            vol = payload["volume"]
            if not isinstance(vol, int) or isinstance(vol, bool) or not (0 <= vol <= 100):
                errors.append("volume 必须是 [0, 100] 的整数")
        if "emotion" in payload and "emotion" in props:
            enum = props["emotion"].get("enum")
            if enum and payload["emotion"] not in enum:
                errors.append(f"emotion 必须是以下之一：{enum}")
        if "pace" in payload and "pace" in props:
            enum = props["pace"].get("enum")
            if enum and payload["pace"] not in enum:
                errors.append(f"pace 必须是以下之一：{enum}")
        for bool_key in ("should_speak", "end_turn"):
            if bool_key in payload and not isinstance(payload[bool_key], bool):
                errors.append(f"{bool_key} 必须是布尔值")
        return errors


def validate_turn(
    text: str,
    schema: Optional[dict[str, Any]] = None,
    schema_path: Optional[str | Path] = None,
    strict_tts: bool = True,
) -> ValidationResult:
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

    if not parsed.abstract:
        errors.append("abstract 为空")
    if re.search(r"</?(?:think|state|abstract)\b", parsed.abstract, re.I):
        errors.append("abstract 不得嵌套结构标签")
    if not parsed.think:
        warnings.append("think 为空")
    if not parsed.state:
        warnings.append("state 为空")

    return ValidationResult(
        ok=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        parsed=parsed,
    )
