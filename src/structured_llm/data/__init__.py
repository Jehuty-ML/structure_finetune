from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator


def load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str | Path, obj: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def iter_sft_rows(path: str | Path) -> Iterator[dict[str, Any]]:
    data = load_json(path)
    if not isinstance(data, list):
        raise ValueError(f"期望 JSON 数组：{path}")
    for row in data:
        if "input" not in row or "output" not in row:
            raise ValueError(f"行缺少 input/output：{row.get('id')}")
        yield row


def format_user_message(
    input_obj: Any,
    prior_utters: list[str] | None = None,
    *,
    prior_label: str = "Prior",
) -> str:
    """构造用户侧内容：可选前几轮摘要/口播 + JSON 输入。

    prior_label：Echo 用 Prior（口播），Quest 用 Abstract（剧情压缩）。
    """
    parts: list[str] = []
    if prior_utters:
        for i, utter in enumerate(prior_utters, start=1):
            parts.append(f"{prior_label} {i}: {utter}")
    if isinstance(input_obj, str):
        payload = input_obj
    else:
        payload = json.dumps(input_obj, ensure_ascii=False)
    parts.append(f"User: {payload}")
    return "\n".join(parts)


from .generate_echo import generate_dataset, split_train_val  # noqa: E402
from . import generate_quest as _quest  # noqa: E402

generate_quest_dataset = _quest.generate_dataset
split_quest_train_val = _quest.split_train_val

__all__ = [
    "load_json",
    "save_json",
    "iter_sft_rows",
    "format_user_message",
    "generate_dataset",
    "split_train_val",
    "generate_quest_dataset",
    "split_quest_train_val",
]
