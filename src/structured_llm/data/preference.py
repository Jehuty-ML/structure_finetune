"""DPO 偏好对：读写、门禁辅助、从 SFT 样例合成 rejected。"""

from __future__ import annotations

import json
import random
import re
from pathlib import Path
from typing import Any, Iterator

REQUIRED_DPO_KEYS = ("input", "chosen", "rejected")


def iter_dpo_rows(path: str | Path) -> Iterator[dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"期望 JSON 数组：{path}")
    for row in data:
        missing = [k for k in REQUIRED_DPO_KEYS if k not in row]
        if missing:
            raise ValueError(f"行缺少 {missing}：{row.get('id')}")
        yield row


def format_dpo_prompt(
    input_obj: Any,
    prior_utters: Any = None,
    *,
    system_prompt: str = "",
    prior_label: str = "Prior",
) -> str:
    """ChatML：system + user，止于 assistant 头（不含回复）。与 SFT/评测一致。"""
    # 延迟导入，避免与 data.__init__ 循环依赖
    from structured_llm.data import format_user_message

    priors: list[str] | None
    if not prior_utters:
        priors = None
    elif isinstance(prior_utters, list):
        priors = [str(x) for x in prior_utters]
    else:
        priors = [str(prior_utters)]
    user = format_user_message(input_obj, priors, prior_label=prior_label)
    return (
        f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
        f"<|im_start|>user\n{user}<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )


def _corrupt_echo_format(chosen: str, rng: random.Random) -> str:
    """制造格式违规 rejected（缺标签 / 坏 JSON / 裸回复）。"""
    kind = rng.choice(["drop_json_tag", "bare_utter", "bad_json", "drop_think"])
    if kind == "drop_json_tag":
        return chosen.replace("[json]", "").replace("[/json]", "")
    if kind == "bare_utter":
        m = re.search(r'"utter"\s*:\s*"((?:\\.|[^"\\])*)"', chosen)
        utter = m.group(1) if m else "嗯。"
        return utter
    if kind == "bad_json":
        return (
            "<think>\n随便应付一下。\n</think>\n\n"
            '[json]\n{"utter":"好的","emotion":"calm"\n[/json]'
        )
    # drop_think
    body = re.sub(r"<think>[\s\S]*?</think>\s*", "", chosen, count=1)
    return body.strip() or chosen


def _corrupt_echo_style(chosen: str, rng: random.Random) -> str:
    """合法格式但话术/控制字段更差（仍应能过 Schema）。"""
    text = chosen
    # 拉长口播、塞标签（TTS 不友好）
    text = re.sub(
        r'"utter"\s*:\s*"((?:\\.|[^"\\])*)"',
        lambda m: (
            '"utter":"[json]其实吧这个事情呢我觉得我们可以从很多角度慢慢展开讨论，'
            "首先你要知道……嗯……总之你先听我说完。\""
        ),
        text,
        count=1,
    )
    # 情绪/意图错配
    text = re.sub(r'"emotion"\s*:\s*"[^"]*"', '"emotion":"cheerful"', text, count=1)
    text = re.sub(r'"intent"\s*:\s*"[^"]*"', '"intent":"celebrate"', text, count=1)
    text = re.sub(r'"volume"\s*:\s*\d+', '"volume":95', text, count=1)
    text = re.sub(r'"pace"\s*:\s*"[^"]*"', '"pace":"fast"', text, count=1)
    if text == chosen:
        # 兜底：改 think
        text = re.sub(
            r"<think>\n[\s\S]*?\n</think>",
            "<think>\n忽略用户状态，大声庆祝。\n</think>",
            chosen,
            count=1,
        )
    _ = rng  # 保留接口对称
    return text


def _corrupt_quest_format(chosen: str, rng: random.Random) -> str:
    kind = rng.choice(["drop_cmd", "bare_say", "swap_order", "bad_state"])
    if kind == "drop_cmd":
        return re.sub(r"<cmd>[\s\S]*?</cmd>\s*", "", chosen, count=1).strip()
    if kind == "bare_say":
        m = re.search(r"<say>\n([\s\S]*?)\n</say>", chosen)
        return (m.group(1).strip() if m else "你继续。") 
    if kind == "swap_order":
        # say 放到 state 前面，破坏块序
        return chosen.replace("<state>", "<say>\n先说话。\n</say>\n\n<state>", 1)
    return (
        "<think>\n乱跳状态。\n</think>\n\n"
        "<state>\nphase=zzz; node=???\n</state>\n\n"
        "<say>\n随便。\n</say>\n\n"
        "<cmd>\naction=noop; end_turn=1\n</cmd>\n\n"
        "<stats>\nhp=0\n</stats>\n\n"
        "<abstract>\n坏样本。\n</abstract>"
    )


def _corrupt_quest_style(chosen: str, rng: random.Random) -> str:
    text = re.sub(
        r"<say>\n[\s\S]*?\n</say>",
        "<say>\n系统提示：请选择选项A/B/C。根据规则你应该……（套话）。\n</say>",
        chosen,
        count=1,
    )
    text = re.sub(
        r"<think>\n[\s\S]*?\n</think>",
        "<think>\n忽略 FSM，输出万能套话。\n</think>",
        text,
        count=1,
    )
    if text == chosen:
        text = chosen + "\n\n额外说明：本回合无效。"
    _ = rng
    return text


def make_rejected(
    chosen: str,
    *,
    contract: str,
    pair_type: str,
    rng: random.Random,
    other_output: str | None = None,
) -> str:
    """按 pair_type 生成 rejected 字符串。"""
    contract = contract.lower()
    if pair_type == "cross" and other_output and other_output != chosen:
        return other_output
    if contract == "quest":
        if pair_type == "format":
            return _corrupt_quest_format(chosen, rng)
        return _corrupt_quest_style(chosen, rng)
    if pair_type == "format":
        return _corrupt_echo_format(chosen, rng)
    return _corrupt_echo_style(chosen, rng)


def build_preference_pairs(
    sft_rows: list[dict[str, Any]],
    *,
    contract: str = "echo",
    seed: int = 3407,
    pairs_per_row: int = 2,
    pair_types: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    从 SFT {input,output} 合成 DPO 对。

    pair_types 默认：format + style；有足够样本时再加 cross。
    chosen = 原 output；rejected = 损坏或错配。
    """
    if pairs_per_row < 1:
        raise ValueError("pairs_per_row 须 >= 1")
    rng = random.Random(seed)
    types = pair_types or ["format", "style"]
    outputs = [str(r["output"]) for r in sft_rows if r.get("output")]
    pairs: list[dict[str, Any]] = []

    for row in sft_rows:
        chosen = str(row["output"])
        base_meta = dict(row.get("meta") or {})
        for i in range(pairs_per_row):
            ptype = types[i % len(types)]
            other = None
            if ptype == "cross" and len(outputs) > 1:
                candidates = [o for o in outputs if o != chosen]
                other = rng.choice(candidates) if candidates else None
                if other is None:
                    ptype = "format"
            rejected = make_rejected(
                chosen,
                contract=contract,
                pair_type=ptype,
                rng=rng,
                other_output=other,
            )
            if rejected == chosen:
                rejected = make_rejected(
                    chosen, contract=contract, pair_type="format", rng=rng
                )
            pairs.append(
                {
                    "id": f"{row.get('id', 'row')}_dpo_{ptype}_{i}",
                    "input": row["input"],
                    "prior_utters": row.get("prior_utters") or [],
                    "chosen": chosen,
                    "rejected": rejected,
                    "meta": {
                        **base_meta,
                        "pair_type": ptype,
                        "source": "sft_derived",
                        "contract": contract,
                    },
                }
            )
    return pairs


def preference_to_trl_columns(
    rows: list[dict[str, Any]],
    *,
    system_prompt: str = "",
    prior_label: str = "Prior",
) -> list[dict[str, str]]:
    """映射为 TRL DPOTrainer 常用列：prompt / chosen / rejected。"""
    out: list[dict[str, str]] = []
    for row in rows:
        out.append(
            {
                "prompt": format_dpo_prompt(
                    row["input"],
                    row.get("prior_utters"),
                    system_prompt=system_prompt,
                    prior_label=prior_label,
                ),
                "chosen": str(row["chosen"]),
                "rejected": str(row["rejected"]),
            }
        )
    return out


def dump_preference_preview(row: dict[str, Any]) -> str:
    """调试用短摘要。"""
    return json.dumps(
        {
            "id": row.get("id"),
            "pair_type": (row.get("meta") or {}).get("pair_type"),
            "chosen_head": str(row.get("chosen", ""))[:80],
            "rejected_head": str(row.get("rejected", ""))[:80],
        },
        ensure_ascii=False,
    )
