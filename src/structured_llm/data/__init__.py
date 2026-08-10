from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator


def load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def iter_sft_rows(path: str | Path) -> Iterator[dict[str, Any]]:
    data = load_json(path)
    if not isinstance(data, list):
        raise ValueError(f"期望 JSON 数组：{path}")
    for row in data:
        if "input" not in row or "output" not in row:
            raise ValueError(f"行缺少 input/output：{row.get('id')}")
        yield row


def format_user_message(input_obj: Any, abstracts: list[str] | None = None) -> str:
    """构造用户侧内容：可选 abstract 记忆 + JSON 输入。"""
    parts: list[str] = []
    if abstracts:
        for i, abstract in enumerate(abstracts, start=1):
            parts.append(f"Abstract {i}: {abstract}")
    if isinstance(input_obj, str):
        payload = input_obj
    else:
        payload = json.dumps(input_obj, ensure_ascii=False)
    parts.append(f"User: {payload}")
    return "\n".join(parts)
