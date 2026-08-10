"""Quest RPG 多块回合解析：think → state → say → cmd → stats → abstract。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

from .kv import parse_kv_line

_BLOCK_RE = re.compile(
    r"<think>\s*(?P<think>.*?)\s*</think>\s*"
    r"<state>\s*(?P<state>.*?)\s*</state>\s*"
    r"<say>\s*(?P<say>.*?)\s*</say>\s*"
    r"<cmd>\s*(?P<cmd>.*?)\s*</cmd>\s*"
    r"<stats>\s*(?P<stats>.*?)\s*</stats>\s*"
    r"<abstract>\s*(?P<abstract>.*?)\s*</abstract>\s*\Z",
    re.DOTALL,
)


@dataclass
class ParsedQuestTurn:
    think: str
    state: dict[str, str]
    say: str
    cmd: dict[str, str]
    stats: dict[str, str]
    abstract: str
    raw_state: str
    raw_cmd: str
    raw_stats: str


def parse_quest_turn(text: str) -> ParsedQuestTurn:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("回合内容为空")
    normalized = text.strip().replace("\r\n", "\n")
    match = _BLOCK_RE.match(normalized)
    if not match:
        raise ValueError(
            "回合不符合约定顺序："
            "<think> -> <state> -> <say> -> <cmd> -> <stats> -> <abstract>"
        )
    raw_state = match.group("state").strip()
    raw_cmd = match.group("cmd").strip()
    raw_stats = match.group("stats").strip()
    try:
        state = parse_kv_line(raw_state)
        cmd = parse_kv_line(raw_cmd)
        stats = parse_kv_line(raw_stats)
    except ValueError as exc:
        raise ValueError(f"键值块解析失败：{exc}") from exc

    return ParsedQuestTurn(
        think=match.group("think").strip(),
        state=state,
        say=match.group("say").strip(),
        cmd=cmd,
        stats=stats,
        abstract=match.group("abstract").strip(),
        raw_state=raw_state,
        raw_cmd=raw_cmd,
        raw_stats=raw_stats,
    )


def try_parse_quest_turn(
    text: str,
) -> tuple[Optional[ParsedQuestTurn], Optional[str]]:
    try:
        return parse_quest_turn(text), None
    except ValueError as exc:
        return None, str(exc)
