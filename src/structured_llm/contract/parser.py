from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Optional


_BLOCK_RE = re.compile(
    r"<think>\s*(?P<think>.*?)\s*</think>\s*"
    r"<state>\s*(?P<state>.*?)\s*</state>\s*"
    r"(?P<json>\{.*?\})\s*"
    r"<abstract>\s*(?P<abstract>.*?)\s*</abstract>\s*\Z",
    re.DOTALL,
)


@dataclass
class ParsedTurn:
    think: str
    state: str
    payload: dict[str, Any]
    abstract: str
    raw_json: str


def parse_turn(text: str) -> ParsedTurn:
    """
    Parse a multi-block Echo-style turn.

    Raises ValueError if the outer structure cannot be recovered.
    """
    if not isinstance(text, str) or not text.strip():
        raise ValueError("empty turn")

    normalized = text.strip().replace("\r\n", "\n")
    match = _BLOCK_RE.match(normalized)
    if not match:
        raise ValueError(
            "turn does not match required order: "
            "<think> -> <state> -> JSON -> <abstract>"
        )

    raw_json = match.group("json").strip()
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON block is not valid JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError("JSON block must be an object")

    return ParsedTurn(
        think=match.group("think").strip(),
        state=match.group("state").strip(),
        payload=payload,
        abstract=match.group("abstract").strip(),
        raw_json=raw_json,
    )


def try_parse_turn(text: str) -> tuple[Optional[ParsedTurn], Optional[str]]:
    try:
        return parse_turn(text), None
    except ValueError as exc:
        return None, str(exc)
