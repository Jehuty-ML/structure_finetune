from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Optional


# v3：think → [json]{...}[/json]（已移除 state / abstract）
_BLOCK_RE = re.compile(
    r"<think>\s*(?P<think>.*?)\s*</think>\s*"
    r"\[json\]\s*(?P<json>\{.*?\})\s*\[/json\]\s*\Z",
    re.DOTALL,
)


@dataclass
class ParsedTurn:
    think: str
    payload: dict[str, Any]
    raw_json: str


def parse_turn(text: str) -> ParsedTurn:
    """
    解析 Echo v3 多块回合：think → [json]…[/json]。

    外层结构无法恢复时抛出 ValueError。
    """
    if not isinstance(text, str) or not text.strip():
        raise ValueError("回合内容为空")

    normalized = text.strip().replace("\r\n", "\n")
    match = _BLOCK_RE.match(normalized)
    if not match:
        raise ValueError(
            "回合不符合约定顺序：<think> -> [json]{...}[/json]"
        )

    raw_json = match.group("json").strip()
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON 块不是合法 JSON：{exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError("JSON 块必须是对象")

    return ParsedTurn(
        think=match.group("think").strip(),
        payload=payload,
        raw_json=raw_json,
    )


def try_parse_turn(text: str) -> tuple[Optional[ParsedTurn], Optional[str]]:
    try:
        return parse_turn(text), None
    except ValueError as exc:
        return None, str(exc)
