"""Echo 服务层：解析、假 TTS、真机对话回合。"""

from __future__ import annotations

from structured_llm.serve.chat import (
    build_user_input,
    guess_emotion,
    run_echo_turn,
    should_force_mute,
)
from structured_llm.serve.response import (
    fake_tts_consume,
    parse_generation_to_response,
)

__all__ = [
    "parse_generation_to_response",
    "fake_tts_consume",
    "run_echo_turn",
    "build_user_input",
    "guess_emotion",
    "should_force_mute",
]
