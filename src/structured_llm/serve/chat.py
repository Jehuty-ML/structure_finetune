"""真机对话回合：生成 → 契约解析 → 假 TTS / 假引擎。"""

from __future__ import annotations

from typing import Any, Callable, Optional

from structured_llm.data import format_user_message
from structured_llm.serve.response import (
    fake_engine_consume,
    fake_tts_consume,
    parse_generation_to_response,
    parse_quest_generation_to_response,
)


def build_user_input(
    user_text: str,
    *,
    turn: int,
    can_speak: bool,
    user_emotion: str = "neutral",
) -> dict[str, Any]:
    return {
        "user_text": user_text,
        "user_emotion": user_emotion,
        "session": {"energy": 55, "bond": 4, "turn": turn},
        "device": {"can_speak": can_speak, "interruptible": can_speak},
    }


def guess_emotion(user_text: str) -> str:
    t = user_text
    if any(k in t for k in ("累", "疲惫", "睡着")):
        return "tired"
    if any(k in t for k in ("开心", "升职", "恭喜", "太棒")):
        return "happy"
    if any(k in t for k in ("不安", "紧张", "悬着", "搬")):
        return "anxious"
    if any(k in t for k in ("朋友", "难过", "糟")):
        return "sad"
    return "neutral"


def should_force_mute(user_text: str) -> bool:
    return any(
        k in user_text for k in ("图书馆", "静音", "别出声", "只回文字", "开会中")
    )


def run_echo_turn(
    *,
    user_text: str,
    generate_fn: Callable[[str, str], str],
    system_prompt: str,
    schema_path: str,
    history: list[tuple[str, str]],
    turn: int,
    can_speak: bool,
    user_emotion: Optional[str] = None,
) -> dict[str, Any]:
    speak = can_speak
    if should_force_mute(user_text):
        speak = False

    emotion = user_emotion or guess_emotion(user_text)
    inp = build_user_input(
        user_text, turn=turn, can_speak=speak, user_emotion=emotion
    )
    # 与训练 / evaluate 一致：只传助手口播 Prior，避免格式漂移
    prior_utters = [a for _, a in history]
    user_msg = format_user_message(inp, prior_utters if prior_utters else None)
    raw = generate_fn(system_prompt, user_msg)
    resp = parse_generation_to_response(
        raw, schema_path=schema_path, input_obj=inp
    )
    out: dict[str, Any] = {
        "ok": bool(resp.get("ok")),
        "input": inp,
        "raw": raw,
        "think": resp.get("think"),
        "voice": resp.get("voice"),
        "tts": None,
        "errors": resp.get("errors") or [],
        "warnings": resp.get("warnings") or [],
        "can_speak": speak,
        "history": list(history),
    }
    if out["ok"] and out["voice"]:
        out["tts"] = fake_tts_consume(out["voice"])
        out["tts_log"] = fake_tts_consume(out["voice"], as_log_line=True)
        utter = str(out["voice"].get("utter") or "")
        out["history"] = history + [(user_text, utter)]
    return out


def build_quest_input(
    user_text: str,
    *,
    fsm: dict[str, str],
    stats: dict[str, str],
) -> dict[str, Any]:
    """Quest 用户侧 JSON：与合成数据 / system prompt 对齐。"""
    return {
        "user_text": user_text,
        "fsm": {
            "phase": str(fsm.get("phase", "explore")),
            "node": str(fsm.get("node", "start")),
        },
        "stats": {
            "hp": str(stats.get("hp", "80")),
            "mp": str(stats.get("mp", "20")),
            "loc": str(stats.get("loc", "未知")),
            "quest": str(stats.get("quest", "")),
        },
    }


def run_quest_turn(
    *,
    user_text: str,
    generate_fn: Callable[[str, str], str],
    system_prompt: str,
    fsm: dict[str, str],
    stats: dict[str, str],
    history: list[tuple[str, str]],
) -> dict[str, Any]:
    """
    Quest 真机一回合。

    history 存 (user_text, abstract)；与训练一致用 Abstract 行作 Prior。
    成功时用输出 state/stats 更新会话，供下一轮输入。
    """
    inp = build_quest_input(user_text, fsm=fsm, stats=stats)
    prior_abstracts = [a for _, a in history]
    user_msg = format_user_message(
        inp,
        prior_abstracts if prior_abstracts else None,
        prior_label="Abstract",
    )
    raw = generate_fn(system_prompt, user_msg)
    resp = parse_quest_generation_to_response(raw, input_obj=inp)
    out: dict[str, Any] = {
        "ok": bool(resp.get("ok")),
        "input": inp,
        "raw": raw,
        "think": resp.get("think"),
        "state": resp.get("state"),
        "say": resp.get("say"),
        "cmd": resp.get("cmd"),
        "stats": resp.get("stats"),
        "abstract": resp.get("abstract"),
        "engine": None,
        "errors": resp.get("errors") or [],
        "warnings": resp.get("warnings") or [],
        "history": list(history),
        "fsm": dict(fsm),
        "session_stats": dict(stats),
    }
    if out["ok"] and out["state"] and out["cmd"] and out["stats"] is not None:
        out["engine"] = fake_engine_consume(
            state=out["state"],
            say=str(out["say"] or ""),
            cmd=out["cmd"],
            stats=out["stats"],
        )
        out["engine_log"] = fake_engine_consume(
            state=out["state"],
            say=str(out["say"] or ""),
            cmd=out["cmd"],
            stats=out["stats"],
            as_log_line=True,
        )
        # 下一拍输入：输出 state → fsm；输出 stats → session
        out["fsm"] = {
            "phase": str(out["state"].get("phase", fsm.get("phase", "explore"))),
            "node": str(out["state"].get("node", fsm.get("node", "start"))),
        }
        out["session_stats"] = {
            "hp": str(out["stats"].get("hp", stats.get("hp", "80"))),
            "mp": str(out["stats"].get("mp", stats.get("mp", "20"))),
            "loc": str(out["stats"].get("loc", stats.get("loc", "未知"))),
            "quest": str(out["stats"].get("quest", stats.get("quest", ""))),
        }
        abstract = str(out.get("abstract") or "")
        out["history"] = history + [(user_text, abstract)]
    return out
