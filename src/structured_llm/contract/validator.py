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
    Minimal JSON Schema checks for the Echo turn object.
    Prefer jsonschema if installed; otherwise enforce required Echo rules.
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
                errors.append(f"missing required property: {key}")

        props = schema.get("properties", {})
        if "utter" in payload and not isinstance(payload["utter"], str):
            errors.append("utter must be a string")
        if "volume" in payload:
            vol = payload["volume"]
            if not isinstance(vol, int) or isinstance(vol, bool) or not (0 <= vol <= 100):
                errors.append("volume must be an integer in [0, 100]")
        if "emotion" in payload and "emotion" in props:
            enum = props["emotion"].get("enum")
            if enum and payload["emotion"] not in enum:
                errors.append(f"emotion must be one of {enum}")
        if "pace" in payload and "pace" in props:
            enum = props["pace"].get("enum")
            if enum and payload["pace"] not in enum:
                errors.append(f"pace must be one of {enum}")
        for bool_key in ("should_speak", "end_turn"):
            if bool_key in payload and not isinstance(payload[bool_key], bool):
                errors.append(f"{bool_key} must be a boolean")
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
            errors.append("utter must not contain structural tags")
        if strict_tts and _STAGE_DIR.search(utter):
            errors.append(
                "utter contains parenthetical stage directions (unsafe for TTS)"
            )

    if not parsed.abstract:
        errors.append("abstract is empty")
    if re.search(r"</?(?:think|state|abstract)\b", parsed.abstract, re.I):
        errors.append("abstract must not nest structural tags")
    if not parsed.think:
        warnings.append("think is empty")
    if not parsed.state:
        warnings.append("state is empty")

    return ValidationResult(
        ok=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        parsed=parsed,
    )
