"""解析 `key=value; key2=value2` 行。"""

from __future__ import annotations

from typing import Any


def parse_kv_line(text: str) -> dict[str, str]:
    """将分号分隔的 key=value 解析为字符串字典；忽略空段。"""
    out: dict[str, str] = {}
    if not text or not str(text).strip():
        return out
    for part in str(text).replace("\n", ";").split(";"):
        piece = part.strip()
        if not piece:
            continue
        if "=" not in piece:
            raise ValueError(f"非法键值段（缺 =）：{piece!r}")
        key, _, val = piece.partition("=")
        key = key.strip()
        val = val.strip()
        if not key:
            raise ValueError(f"空键：{piece!r}")
        out[key] = val
    return out


def format_kv(data: dict[str, Any], *, order: list[str] | None = None) -> str:
    keys = list(order) if order else list(data.keys())
    for k in data:
        if k not in keys:
            keys.append(k)
    parts = [f"{k}={data[k]}" for k in keys if k in data]
    return "; ".join(parts)
