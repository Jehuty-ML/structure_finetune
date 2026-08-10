#!/usr/bin/env python3
"""向本地 Echo API 发一条演示请求（httpx）。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT = {
    "user_text": "好累，别让我想太多。",
    "user_emotion": "tired",
    "session": {"energy": 22, "bond": 4, "turn": 2},
    "device": {"can_speak": True, "interruptible": True},
}

DEFAULT_RAW = """<think>
用户疲惫；短句低音量；intent=comfort。
</think>

[json]
{"utter":"没事，我在这儿。你先歇着。","emotion":"gentle","volume":30,"pace":"slow","should_speak":true,"intent":"comfort","ui_mode":"speak","end_turn":false}
[/json]"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--mode",
        choices=("parse", "turn", "fixture"),
        default="fixture",
        help="parse=只解析文本；turn/fixture=用户 JSON + raw_output",
    )
    parser.add_argument("--text-file", default="", help="原始生成文本文件")
    args = parser.parse_args()

    try:
        import httpx
    except ImportError as exc:
        raise SystemExit("需要 httpx：pip install httpx") from exc

    if args.text_file:
        raw = Path(args.text_file).read_text(encoding="utf-8")
    else:
        raw = DEFAULT_RAW

    if args.mode == "parse":
        url = f"{args.base_url.rstrip('/')}/v1/parse"
        body = {"text": raw, "input": DEFAULT_INPUT}
    else:
        url = f"{args.base_url.rstrip('/')}/v1/turn"
        body = {"input": DEFAULT_INPUT, "raw_output": raw}

    r = httpx.post(url, json=body, timeout=30.0)
    print(f"HTTP {r.status_code}")
    try:
        data = r.json()
    except Exception:
        print(r.text)
        raise SystemExit(1)
    print(json.dumps(data, ensure_ascii=False, indent=2))
    if not data.get("ok"):
        raise SystemExit(1)
    tts = data.get("tts") or {}
    print(
        "\n# 假 TTS 通道摘要:",
        f"utter={tts.get('utter')!r}",
        f"emotion={tts.get('emotion')}",
        f"volume={tts.get('volume')}",
    )


if __name__ == "__main__":
    main()
