"""把攻击旁白打磨成四拍衔接，并去掉「交换后」等套话。"""

from __future__ import annotations

import hashlib
import re
from typing import Any


_ACT_MAP: list[tuple[str, str]] = [
    ("冷冻光", "挥出冷冻光刃砍向灰狼"),
    ("火焰球", "抛出火焰球砸向灰狼"),
    ("毒针", "射出毒针刺向灰狼"),
    ("冰锥", "凝出冰锥扎向灰狼"),
    ("雷击", "拍出雷击掌打向灰狼"),
    ("风刃", "甩出风刃斩向灰狼"),
    ("影刺", "掷出影刺刺向灰狼"),
    ("寒霜箭", "射出寒霜箭钉向灰狼"),
    ("裂地斩", "使出裂地斩劈向灰狼"),
    ("光刃", "挥出光刃斩向灰狼"),
    ("爆炎拳", "打出爆炎拳轰向灰狼"),
    ("普攻", "上前普通一击砍向灰狼"),
    ("挥剑", "挥剑砍向灰狼"),
    ("砸", "抡起武器砸向灰狼"),
    ("刺", "挺剑刺向灰狼"),
    ("斩", "横斩砍向灰狼"),
    ("踢", "抬脚踹向灰狼"),
    ("砍", "举刀砍向灰狼"),
    ("打", "冲上前攻向灰狼"),
    ("攻击", "主动出手攻向灰狼"),
]

_HITS = [
    "刃口切开它的肩侧皮毛",
    "力道结实地砸在肋侧",
    "锋刃擦过颈侧带起血线",
    "击中前腿，它一个踉跄",
    "命中胸侧，灰狼痛吼一声",
    "砍在旧伤附近，伤口扩大",
    "打中肩甲接缝，霜粉/尘土飞起",
    "准确命中侧腹浅层",
]

_ENEMY = [
    "扑咬你的护臂，牙关咬紧",
    "侧身撞来，肩头撞在你胸口",
    "爪扫你的小腿外侧",
    "低吼着撕扯你的披风下摆连带皮肉",
    "前扑压住你半步，咬向肩膀护甲",
    "甩头反击，鼻骨撞到你腕骨",
    "绕到侧面抓挠你的手臂",
    "借痛劲猛扑，扑到你胸甲上",
]


def _pick(seed: str, items: list[str]) -> str:
    h = int(hashlib.md5(seed.encode("utf-8")).hexdigest(), 16)
    return items[h % len(items)]


def _act_from_user(user_text: str) -> str:
    for key, phrase in _ACT_MAP:
        if key in user_text:
            return phrase
    return "主动出手攻向灰狼"


def polish_attack_texts(
    user_text: str,
    say: str,
    think: str,
    abstract: str,
    *,
    sid: str = "",
) -> tuple[str, str, str]:
    """返回 (say, think, abstract)。"""
    deal_m = re.search(r"造成\s*(\d+)\s*点", say)
    take_m = re.search(r"受到\s*(\d+)\s*点", say)
    deal = deal_m.group(1) if deal_m else "12"
    take = take_m.group(1) if take_m else "8"
    seed = sid or user_text
    act = _act_from_user(user_text)
    hit = _pick(seed + ":hit", _HITS).replace("霜粉/尘土", "尘土")
    if "冷冻" in user_text or "冰" in user_text or "寒霜" in user_text:
        hit = _pick(seed + ":ice", [
            "霜光炸在肩侧，皮毛结起薄霜",
            "冰屑迸溅，击中肋侧",
            "寒气扎进前腿，它站立不稳",
        ])
    if "火" in user_text or "炎" in user_text:
        hit = _pick(seed + ":fire", [
            "焦毛味散开，击中肋侧",
            "火光燎过肩毛，伤口发红",
        ])
    enemy = _pick(seed + ":enemy", _ENEMY)
    new_say = (
        f"你{act}，造成{deal}点伤害，{hit}。"
        f"狼随即{enemy}，你受到{take}点伤害。"
        f"请继续行动。"
    )
    new_think = (
        "已在 combat；旁白四拍：你出手→造成伤害→狼反击→你受伤并回操作；"
        "node=round_player；禁止套话。"
    )
    # think 也禁止残留「交换」
    new_think = new_think.replace("交换", "")
    new_abs = (
        abstract.replace("交换完毕", "四拍完成")
        .replace("全交换", "攻防四拍")
        .replace("交换完成", "告一段落")
        .replace("交换结束", "")
        .replace("交换后", "")
        .replace("交换", "")
        .replace("敌方回合", "攻防后回玩家")
        .replace("轮到它", "攻防后")
    )
    while "  " in new_abs:
        new_abs = new_abs.replace("  ", " ")
    new_abs = new_abs.replace("；；", "；").strip("；").strip()
    if not new_abs or len(new_abs) < 8:
        new_abs = "攻防四拍完成；仍 combat；回玩家操作。"
    return new_say, new_think, new_abs


def polish_attack_row(row: dict[str, Any]) -> dict[str, Any]:
    if row.get("meta", {}).get("rule_id") != "combat_attack":
        return row
    from structured_llm.data.generate_quest import render_quest_output
    from structured_llm.contract.quest_parser import try_parse_quest_turn

    parsed, err = try_parse_quest_turn(row["output"])
    if err or parsed is None:
        return row
    say, think, abstract = polish_attack_texts(
        str(row["input"].get("user_text", "")),
        parsed.say,
        parsed.think,
        parsed.abstract,
        sid=str(row.get("id", "")),
    )
    row = dict(row)
    row["output"] = render_quest_output(
        think,
        dict(parsed.state),
        say,
        dict(parsed.cmd),
        dict(parsed.stats),
        abstract,
    )
    return row
