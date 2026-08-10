#!/usr/bin/env python3
"""本地服务冒烟：health / 非法解析 / 静音 turn。"""

from __future__ import annotations

import sys

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"


def main() -> None:
    r = httpx.get(f"{BASE}/health", timeout=10.0)
    assert r.status_code == 200 and r.json().get("status") == "ok", r.text
    print("health ok")

    bad = httpx.post(f"{BASE}/v1/parse", json={"text": "not a contract"}, timeout=10.0)
    bj = bad.json()
    assert bj.get("ok") is False and bj.get("errors"), bj
    print("bad parse ok:", bj["errors"][0][:60])

    raw = (
        "<think>\nmute\n</think>\n\n[json]\n"
        '{"utter":"好，已静音，我只回文字。","emotion":"calm","volume":0,'
        '"pace":"normal","should_speak":false,"intent":"chat",'
        '"ui_mode":"text_only","end_turn":false}\n[/json]'
    )
    inp = {
        "user_text": "图书馆模式。",
        "user_emotion": "neutral",
        "session": {"energy": 50, "bond": 3, "turn": 9},
        "device": {"can_speak": False, "interruptible": False},
    }
    ok = httpx.post(
        f"{BASE}/v1/turn",
        json={"input": inp, "raw_output": raw},
        timeout=10.0,
    )
    d = ok.json()
    assert d.get("ok") is True, d
    assert d["tts"]["should_speak"] is False
    assert d["voice"]["ui_mode"] == "text_only"
    print("mute turn ok; tts=", d["tts"])
    print("ALL_PASS")


if __name__ == "__main__":
    main()
