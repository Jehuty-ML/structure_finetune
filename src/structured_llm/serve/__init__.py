"""服务层：解析、假 TTS / 假引擎、真机对话回合。"""

from __future__ import annotations

from structured_llm.serve.chat import (
    build_quest_input,
    build_user_input,
    guess_emotion,
    run_echo_turn,
    run_quest_turn,
    should_force_mute,
)
from structured_llm.serve.response import (
    fake_engine_consume,
    fake_tts_consume,
    parse_generation_to_response,
    parse_quest_generation_to_response,
)

__all__ = [
    "parse_generation_to_response",
    "parse_quest_generation_to_response",
    "fake_tts_consume",
    "fake_engine_consume",
    "run_echo_turn",
    "run_quest_turn",
    "build_user_input",
    "build_quest_input",
    "guess_emotion",
    "should_force_mute",
]
