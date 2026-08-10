"""真机对话回合：生成 → 契约解析 → 假 TTS。"""

from __future__ import annotations

from typing import Any, Callable, Optional

from structured_llm.data import format_user_message
from structured_llm.serve.response import (
    fake_tts_consume,
    parse_generation_to_response,
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
