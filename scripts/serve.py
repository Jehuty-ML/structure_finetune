#!/usr/bin/env python3
"""最小服务草稿：将原始生成文本校验并解析为 VoiceTurn。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from structured_llm.serve import parse_generation_to_response


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--text-file",
        help="原始模型生成文本路径；省略则从标准输入读取",
    )
    parser.add_argument(
        "--schema",
        default=str(ROOT / "schemas" / "echo_turn.schema.json"),
        help="JSON Schema 路径",
    )
    args = parser.parse_args()

    if args.text_file:
        text = Path(args.text_file).read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()

    resp = parse_generation_to_response(text, schema_path=args.schema)
    print(json.dumps(resp, indent=2, ensure_ascii=False))
    raise SystemExit(0 if resp.get("ok") else 1)


if __name__ == "__main__":
    main()
