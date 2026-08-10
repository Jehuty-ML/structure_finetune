"""Echo 模板合成数据（契约 v3：think → [json]…[/json]）。"""

from __future__ import annotations

import json
import random
from typing import Any


SCENARIOS: list[dict[str, Any]] = [
    {
        "tag": "tired",
        "user_emotion": "tired",
        "user_texts": [
            "好累，别让我想太多。",
            "今天太长了，陪我待一会儿。",
            "我快睡着了，轻声点。",
            "能量见底了，说点短的。",
            "先别追问，我就想静一下。",
        ],
        "think": "用户疲惫；短句、低音量、慢语速；意图安抚。",
        "emotion": "gentle",
        "intent": "comfort",
        "ui_mode": "speak",
        "vol": (22, 40),
        "pace": "slow",
        "utters": [
            "没事，我在这儿。你先歇着。",
            "好，我们说短一点。慢慢来。",
            "先喘口气，我不催你。",
            "听到了。你休息，我陪着。",
        ],
        "end_turn": False,
        "mute": False,
    },
    {
        "tag": "happy",
        "user_emotion": "happy",
        "user_texts": [
            "我升职了！",
            "今天面试过了。",
            "终于把项目交付了。",
            "周末要去旅行，好开心。",
            "刚收到好消息。",
        ],
        "think": "简短祝贺；cheerful，音量略高；意图庆祝。",
        "emotion": "cheerful",
        "intent": "celebrate",
        "ui_mode": "speak",
        "vol": (60, 78),
        "pace": "normal",
        "utters": [
            "太棒了，你值得！最开心的点是什么？",
            "恭喜！说一句你现在的心情就好。",
            "好消息！想先庆祝一下吗？",
            "厉害。哪一步最有成就感？",
        ],
        "end_turn": False,
        "mute": False,
    },
    {
        "tag": "anxious",
        "user_emotion": "anxious",
        "user_texts": [
            "这封邮件让我不安。",
            "我是不是想太多了？",
            "明天汇报好紧张。",
            "总觉得漏了什么。",
            "心里一直悬着。",
        ],
        "think": "承认感受，再要一个具体点；意图澄清。",
        "emotion": "concerned",
        "intent": "clarify",
        "ui_mode": "speak",
        "vol": (40, 55),
        "pace": "slow",
        "utters": [
            "不安很正常。最卡你的是哪一句？",
            "我们可以只抓一件事。先说最担心的。",
            "别急着结论。你现在最在意什么？",
            "我在听。把最重的那一点说出来就好。",
        ],
        "end_turn": False,
        "mute": False,
    },
    {
        "tag": "neutral",
        "user_emotion": "neutral",
        "user_texts": [
            "今天天气怎么样？",
            "提醒我喝水。",
            "现在几点合适休息？",
            "随便聊聊也行。",
            "你在吗？",
        ],
        "think": "平静闲聊；正常音量；意图 chat。",
        "emotion": "calm",
        "intent": "chat",
        "ui_mode": "speak",
        "vol": (45, 60),
        "pace": "normal",
        "utters": [
            "在的。你想聊哪一块？",
            "好，我记一下：记得喝水。",
            "可以。你更想听建议还是随便聊？",
            "我在。说一句你现在需要什么。",
        ],
        "end_turn": False,
        "mute": False,
    },
    {
        "tag": "playful",
        "user_emotion": "sad",
        "user_texts": [
            "哄我笑一下。",
            "今天糟透了，整点轻松的。",
            "给我一句不严肃的。",
            "心情差，来点无厘头。",
            "逗我一下，别太重。",
        ],
        "think": "轻度玩笑，避免伤人；意图 joke。",
        "emotion": "playful",
        "intent": "joke",
        "ui_mode": "speak",
        "vol": (55, 68),
        "pace": "normal",
        "utters": [
            "备用方案：零食，或者离谱舞步。你选哪个？",
            "好。要温和玩笑还是离谱一点的？",
            "收到。先给你选择题：茶还是走走？",
            "行。坏日子配小玩笑：今天允许摆烂两分钟。",
        ],
        "end_turn": False,
        "mute": False,
    },
    {
        "tag": "mute",
        "user_emotion": "neutral",
        "user_texts": [
            "图书馆模式。",
            "先别出声，我打字。",
            "静音一下。",
            "开会中，只回文字。",
            "旁边有人，别播。",
        ],
        "think": "不可语音；should_speak=false，ui_mode=text_only。",
        "emotion": "calm",
        "intent": "chat",
        "ui_mode": "text_only",
        "vol": (0, 0),
        "pace": "normal",
        "utters": [
            "好，已静音，我只回文字。",
            "收到，不出声，文字答复。",
            "安静模式开着，我打字回复。",
            "明白，语音关闭，文本继续。",
        ],
        "end_turn": False,
        "mute": True,
    },
    {
        "tag": "end_turn",
        "user_emotion": "neutral",
        "user_texts": [
            "先这样吧，我去忙了。",
            "够了，回头再说。",
            "先挂了，谢谢。",
            "到这儿就好。",
            "我先走一步。",
        ],
        "think": "用户收束；intent=close，end_turn=true。",
        "emotion": "calm",
        "intent": "close",
        "ui_mode": "speak",
        "vol": (40, 55),
        "pace": "normal",
        "utters": [
            "好，你去忙。需要时叫我。",
            "行，回头再聊。",
            "收到，先这样。保重。",
            "好的，我在这儿等你回来。",
        ],
        "end_turn": True,
        "mute": False,
    },
    {
        "tag": "interruptible",
        "user_emotion": "neutral",
        "user_texts": [
            "等等，打断一下。",
            "先停，我插一句。",
            "说到一半，我想改话题。",
            "停一下，换个问题。",
            "别展开了，直接说重点。",
        ],
        "think": "确认打断并缩短；intent=interrupt_ack。",
        "emotion": "neutral",
        "intent": "interrupt_ack",
        "ui_mode": "speak",
        "vol": (48, 62),
        "pace": "fast",
        "utters": [
            "好，我停。你现在最想问什么？",
            "收到打断。直接说重点就行。",
            "行，换题。你先说。",
            "明白，我收短。你的新问题是？",
        ],
        "end_turn": False,
        "mute": False,
    },
]


def _render_output(
    think: str,
    utter: str,
    emotion: str,
    volume: int,
    pace: str,
    should_speak: bool,
    intent: str,
    ui_mode: str,
    end_turn: bool,
) -> str:
    payload = {
        "utter": utter,
        "emotion": emotion,
        "volume": volume,
        "pace": pace,
        "should_speak": should_speak,
        "intent": intent,
        "ui_mode": ui_mode,
        "end_turn": end_turn,
    }
    json_block = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return (
        f"<think>\n{think}\n</think>\n\n"
        f"[json]\n{json_block}\n[/json]"
    )


def build_row_from_scenario(
    sc: dict[str, Any], rng: random.Random, index: int
) -> dict[str, Any]:
    mute = bool(sc["mute"])
    can_speak = not mute
    vol_lo, vol_hi = sc["vol"]
    volume = vol_lo if vol_lo == vol_hi else rng.randint(vol_lo, vol_hi)
    utter = rng.choice(sc["utters"])
    ui_mode = sc["ui_mode"]
    if mute:
        ui_mode = "text_only"
    inp = {
        "user_text": rng.choice(sc["user_texts"]),
        "user_emotion": sc["user_emotion"],
        "session": {
            "energy": rng.randint(15, 90),
            "bond": rng.randint(1, 8),
            "turn": rng.randint(1, 40),
        },
        "device": {"can_speak": can_speak, "interruptible": not mute},
    }
    out = _render_output(
        think=sc["think"],
        utter=utter,
        emotion=sc["emotion"],
        volume=volume,
        pace=sc["pace"],
        should_speak=can_speak,
        intent=sc["intent"],
        ui_mode=ui_mode,
        end_turn=bool(sc["end_turn"]),
    )
    return {
        "id": f"echo_syn_{index:04d}_{sc['tag']}",
        "input": inp,
        "output": out,
        "prior_utters": [],
        "meta": {"scenario": sc["tag"], "contract": "v3"},
    }


# 多轮续写：user 侧带 Prior 口播，教模型承接话题（对齐评测 multi_turn_context）
MULTI_TURN_CHAINS: list[dict[str, Any]] = [
    {
        "tag": "move_friends",
        "rounds": [
            {
                "user_text": "可能要为工作搬去别的城市。",
                "user_emotion": "anxious",
                "think": "承认压力，意图澄清最重的一点。",
                "emotion": "concerned",
                "intent": "clarify",
                "ui_mode": "speak",
                "volume": 50,
                "pace": "normal",
                "utter": "这是大事。眼下最沉的是哪一块？",
                "end_turn": False,
            },
            {
                "user_text": "离开朋友。",
                "user_emotion": "sad",
                "think": "承接搬家话题；安抚并给一个可行动点。",
                "emotion": "gentle",
                "intent": "comfort",
                "ui_mode": "speak",
                "volume": 45,
                "pace": "slow",
                "utter": "想朋友很正常。要不要一起想一个保持联系的法子？",
                "end_turn": False,
            },
        ],
    },
    {
        "tag": "move_friends_v2",
        "rounds": [
            {
                "user_text": "可能要因为工作搬家。",
                "user_emotion": "anxious",
                "think": "先稳住，再问最沉重的部分。",
                "emotion": "concerned",
                "intent": "clarify",
                "ui_mode": "speak",
                "volume": 48,
                "pace": "normal",
                "utter": "听起来压力不小。最让你沉的是哪一点？",
                "end_turn": False,
            },
            {
                "user_text": "怕离开朋友。",
                "user_emotion": "sad",
                "think": "用户点出朋友；安抚并提保持联系。",
                "emotion": "gentle",
                "intent": "comfort",
                "ui_mode": "speak",
                "volume": 42,
                "pace": "slow",
                "utter": "舍不得朋友很正常。我们可以一起想怎么保持联系。",
                "end_turn": False,
            },
        ],
    },
    {
        "tag": "move_friends_v3",
        "rounds": [
            {
                "user_text": "工作调动，可能要去别的城市。",
                "user_emotion": "anxious",
                "think": "澄清最重的一块。",
                "emotion": "concerned",
                "intent": "clarify",
                "ui_mode": "speak",
                "volume": 52,
                "pace": "normal",
                "utter": "这事不小。眼下最沉的是哪一块？",
                "end_turn": False,
            },
            {
                "user_text": "离开朋友。",
                "user_emotion": "sad",
                "think": "承接 Prior；comfort + 联系。",
                "emotion": "gentle",
                "intent": "comfort",
                "ui_mode": "speak",
                "volume": 44,
                "pace": "slow",
                "utter": "想朋友没问题。要不要先定一个保持联系的节奏？",
                "end_turn": False,
            },
        ],
    },
    {
        "tag": "tired_shorter",
        "rounds": [
            {
                "user_text": "好累，别让我想太多。",
                "user_emotion": "tired",
                "think": "短句安抚。",
                "emotion": "gentle",
                "intent": "comfort",
                "ui_mode": "speak",
                "volume": 30,
                "pace": "slow",
                "utter": "没事，我在这儿。你先歇着。",
                "end_turn": False,
            },
            {
                "user_text": "再说短一点。",
                "user_emotion": "tired",
                "think": "承接疲惫；更短。",
                "emotion": "gentle",
                "intent": "comfort",
                "ui_mode": "speak",
                "volume": 28,
                "pace": "slow",
                "utter": "好。我陪着，你休息。",
                "end_turn": False,
            },
        ],
    },
    {
        "tag": "happy_detail",
        "rounds": [
            {
                "user_text": "我升职了！",
                "user_emotion": "happy",
                "think": "祝贺并邀请一句感受。",
                "emotion": "cheerful",
                "intent": "celebrate",
                "ui_mode": "speak",
                "volume": 70,
                "pace": "normal",
                "utter": "太棒了，你值得！最开心的点是什么？",
                "end_turn": False,
            },
            {
                "user_text": "终于被看见了。",
                "user_emotion": "happy",
                "think": "承接庆祝；肯定被看见。",
                "emotion": "cheerful",
                "intent": "celebrate",
                "ui_mode": "speak",
                "volume": 68,
                "pace": "normal",
                "utter": "被看见的感觉真棒。今晚要不要小小庆祝一下？",
                "end_turn": False,
            },
        ],
    },
    {
        "tag": "anxious_one_thing",
        "rounds": [
            {
                "user_text": "心里一直悬着。",
                "user_emotion": "anxious",
                "think": "引导说一个具体点。",
                "emotion": "concerned",
                "intent": "clarify",
                "ui_mode": "speak",
                "volume": 48,
                "pace": "slow",
                "utter": "我们可以只抓一件事。先说最担心的。",
                "end_turn": False,
            },
            {
                "user_text": "明天汇报。",
                "user_emotion": "anxious",
                "think": "承接汇报焦虑；再收窄。",
                "emotion": "concerned",
                "intent": "clarify",
                "ui_mode": "speak",
                "volume": 46,
                "pace": "slow",
                "utter": "汇报最卡你的是开场，还是提问环节？",
                "end_turn": False,
            },
        ],
    },
]


def _device_ok() -> dict[str, Any]:
    return {"can_speak": True, "interruptible": True}


def build_rows_from_chain(
    chain: dict[str, Any], rng: random.Random, start_index: int
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    prior: list[str] = []
    tag = chain["tag"]
    for i, rnd in enumerate(chain["rounds"]):
        turn = rng.randint(1, 20) + i
        inp = {
            "user_text": rnd["user_text"],
            "user_emotion": rnd["user_emotion"],
            "session": {
                "energy": rng.randint(30, 80),
                "bond": rng.randint(3, 7),
                "turn": turn,
            },
            "device": _device_ok(),
        }
        out = _render_output(
            think=rnd["think"],
            utter=rnd["utter"],
            emotion=rnd["emotion"],
            volume=int(rnd["volume"]),
            pace=rnd["pace"],
            should_speak=True,
            intent=rnd["intent"],
            ui_mode=rnd["ui_mode"],
            end_turn=bool(rnd["end_turn"]),
        )
        rows.append(
            {
                "id": f"echo_mt_{start_index + i:04d}_{tag}_r{i + 1}",
                "input": inp,
                "output": out,
                "prior_utters": list(prior),
                "meta": {
                    "scenario": tag,
                    "contract": "v3",
                    "multi_turn": True,
                    "round": i + 1,
                },
            }
        )
        prior.append(rnd["utter"])
    return rows


def generate_multi_turn_rows(seed: int = 3407) -> list[dict[str, Any]]:
    """每个链条生成一轮+二轮样本；并对二轮做若干近义复述。"""
    rng = random.Random(seed + 99)
    rows: list[dict[str, Any]] = []
    idx = 1
    for chain in MULTI_TURN_CHAINS:
        built = build_rows_from_chain(chain, rng, idx)
        rows.extend(built)
        idx += len(built)
        # 复述第 2 轮（同一 Prior，换口播措辞）
        if len(built) >= 2:
            r2 = built[1]
            variants = [
                (
                    "想朋友很正常。要不要一起想一个保持联系的法子？",
                    "承接 Prior 的搬家/朋友；comfort。",
                ),
                (
                    "舍不得朋友很正常。我们可以一起想怎么保持联系。",
                    "用户怕离开朋友；安抚并提联系。",
                ),
                (
                    "朋友这块最沉。先一起定一个保持联系的小办法？",
                    "点明朋友；给可行动点。",
                ),
            ]
            if chain["tag"].startswith("move_friends"):
                for utter, think in variants:
                    payload = dict(r2)
                    payload = {
                        **r2,
                        "id": f"echo_mt_{idx:04d}_{chain['tag']}_r2var",
                        "output": _render_output(
                            think=think,
                            utter=utter,
                            emotion="gentle",
                            volume=rng.randint(40, 48),
                            pace="slow",
                            should_speak=True,
                            intent="comfort",
                            ui_mode="speak",
                            end_turn=False,
                        ),
                        "prior_utters": list(r2["prior_utters"]),
                        "meta": {
                            **r2["meta"],
                            "variant": True,
                        },
                    }
                    rows.append(payload)
                    idx += 1
    return rows


def generate_dataset(count: int, seed: int = 3407) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    mt_rows = generate_multi_turn_rows(seed=seed)
    # 单轮占预算的大部分；多轮样本追加（可略超 count，保证多轮覆盖）
    single_budget = max(count - len(mt_rows), count // 2)
    rows: list[dict[str, Any]] = []
    for i, sc in enumerate(SCENARIOS):
        if len(rows) >= single_budget:
            break
        rows.append(build_row_from_scenario(sc, random.Random(seed + i), i + 1))
    while len(rows) < single_budget:
        idx = len(rows) + 1
        sc = rng.choice(SCENARIOS)
        rows.append(build_row_from_scenario(sc, rng, idx))
    rows.extend(mt_rows)
    return rows


def split_train_val(
    rows: list[dict[str, Any]], val_ratio: float = 0.15, seed: int = 3407
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rng = random.Random(seed)
    shuffled = list(rows)
    rng.shuffle(shuffled)
    n_val = max(1, int(len(shuffled) * val_ratio))
    if n_val >= len(shuffled):
        n_val = max(1, len(shuffled) // 5)
    val = shuffled[:n_val]
    train = shuffled[n_val:]
    return train, val

