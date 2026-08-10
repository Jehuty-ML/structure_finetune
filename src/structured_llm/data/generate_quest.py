"""Quest RPG 模板合成数据。"""

from __future__ import annotations

import random
from typing import Any

from structured_llm.contract.kv import format_kv


SCENARIOS: list[dict[str, Any]] = [
    {
        "tag": "explore_fork",
        "weight": 1.6,
        "user_texts": [
            "我往前走。",
            "看看左边的小路。",
            "朝山洞方向走。",
            "往雾里走两步。",
            "停在岔路口看看。",
        ],
        "fsm_in": {"phase": "explore", "node": "forest_fork"},
        "thinks": [
            "探索路口；保持 explore；action=prompt_choice；禁止 advance（advance 只用于 cutscene）。",
            "仍在 explore/forest_fork；给玩家选路菜单；cmd 只能是 prompt_choice，绝不是 advance。",
        ],
        "state": {
            "phase": "explore",
            "node": "forest_fork",
            "allowed": "move,talk,open_inventory",
        },
        "says": [
            "这条路通向山洞。要进去吗？",
            "林雾更浓了。左边是兽径，右边是旧桥。",
            "你还能听见远处的水声。选一条路吧。",
            "脚印分叉了。你停下来打量两边。",
        ],
        "cmd": {"action": "prompt_choice", "target": "cave_entrance", "end_turn": "0"},
        "stats": {
            "hp": "80",
            "mp": "20",
            "loc": "森林路口",
            "quest": "找药草",
            "flags": "has_map",
        },
        "abstracts": [
            "探索中停在森林路口；任务找药草；已有地图；未进洞。",
            "仍在森林路口观望；未开战；任务找药草。",
        ],
    },
    {
        "tag": "explore_enter_cave",
        "weight": 1.0,
        "user_texts": [
            "进山洞。",
            "我选择进洞。",
            "去洞穴里看看。",
            "钻进洞口。",
        ],
        "fsm_in": {"phase": "explore", "node": "forest_fork"},
        "thinks": [
            "玩家选择进洞；仍属探索，节点切到 cave_mouth；action=move。",
        ],
        "state": {
            "phase": "explore",
            "node": "cave_mouth",
            "allowed": "move,talk,open_inventory",
        },
        "says": [
            "洞口阴冷，石壁上有爪痕。你举着火把走进去。",
            "你弯腰钻入洞穴，潮气扑面而来。",
            "火光照亮潮湿石壁，你踏进洞穴入口。",
        ],
        "cmd": {"action": "move", "target": "cave_mouth", "end_turn": "0"},
        "stats": {
            "hp": "80",
            "mp": "18",
            "loc": "洞穴入口",
            "quest": "找药草",
            "flags": "has_map,entered_cave",
        },
        "abstracts": [
            "已进入洞穴入口；任务仍是找药草；地图在身。",
            "人在洞穴入口；探索中；尚未遇敌。",
        ],
    },
    {
        "tag": "combat_start",
        "weight": 1.2,
        "user_texts": [
            "有怪物！",
            "前面跳出一只狼。",
            "战斗开始了。",
            "狼堵住了路。",
            "遇敌了。",
        ],
        "fsm_in": {"phase": "explore", "node": "cave_mouth"},
        "thinks": [
            "遭遇战；phase: explore→combat；node=round_player；action=prompt_choice。",
            "从探索切入战斗；禁止 flee；先给战斗菜单。",
        ],
        "state": {
            "phase": "combat",
            "node": "round_player",
            "allowed": "attack,skill,item,flee",
        },
        "says": [
            "灰狼低吼着挡住去路。轮到你行动。",
            "敌人扑来！请选择攻击、技能、道具或逃跑。",
            "战斗爆发。灰狼盯着你，等你出招。",
        ],
        "cmd": {"action": "prompt_choice", "target": "combat_menu", "end_turn": "0"},
        "stats": {
            "hp": "76",
            "mp": "18",
            "loc": "洞穴入口",
            "quest": "找药草",
            "flags": "has_map,in_combat",
        },
        "abstracts": [
            "战斗开始，玩家回合；地点洞穴入口；任务找药草。",
            "已进入 combat；尚未逃跑；在洞穴入口。",
        ],
    },
    {
        "tag": "combat_attack",
        "weight": 1.0,
        "user_texts": [
            "我攻击。",
            "普通攻击。",
            "砍它一刀。",
            "挥剑。",
            "打它。",
        ],
        "fsm_in": {"phase": "combat", "node": "round_player"},
        "thinks": [
            "玩家攻击；保持 combat；node→round_enemy；action=attack；不是 flee。",
            "仍在战斗中输出伤害；禁止切回 explore。",
        ],
        "state": {
            "phase": "combat",
            "node": "round_enemy",
            "allowed": "attack,skill,item,flee",
        },
        "says": [
            "你挥剑命中，灰狼退后一步。轮到它了。",
            "一击命中要害，敌人怒视着你。",
            "剑刃擦过毛皮，狼发出怒吼。",
        ],
        "cmd": {"action": "attack", "target": "wolf", "end_turn": "0"},
        "stats": {
            "hp": "76",
            "mp": "18",
            "loc": "洞穴入口",
            "quest": "找药草",
            "flags": "has_map,in_combat",
        },
        "abstracts": [
            "战斗中已攻击；进入敌方回合；仍在洞穴入口。",
            "仍在 combat；刚完成 attack；未逃离。",
        ],
    },
    {
        "tag": "dialogue_npc",
        "weight": 0.8,
        "user_texts": [
            "和老人谈谈。",
            "我想问问路。",
            "跟草药师说话。",
        ],
        "fsm_in": {"phase": "explore", "node": "village_square"},
        "thinks": [
            "进入 dialogue；action=talk；不是 combat/flee。",
        ],
        "state": {
            "phase": "dialogue",
            "node": "herbalist_hello",
            "allowed": "talk,open_inventory",
        },
        "says": [
            "草药师推了推眼镜：药草在北谷，小心狼群。",
            "老人说：带上地图，北谷深处有你要的叶子。",
        ],
        "cmd": {"action": "talk", "target": "herbalist", "end_turn": "0"},
        "stats": {
            "hp": "90",
            "mp": "25",
            "loc": "村子广场",
            "quest": "找药草",
            "flags": "has_map,met_herbalist",
        },
        "abstracts": [
            "对话中见过草药师；得知药草在北谷；人在村子广场。",
        ],
    },
    {
        "tag": "shop_buy",
        "weight": 0.7,
        "user_texts": [
            "买一瓶药水。",
            "我要红药。",
            "购买治疗药。",
        ],
        "fsm_in": {"phase": "shop", "node": "shop_main"},
        "thinks": [
            "商店购买；保持 shop；action=buy。",
        ],
        "state": {
            "phase": "shop",
            "node": "shop_main",
            "allowed": "buy,talk",
        },
        "says": [
            "店主递过红药：三枚银币，祝你一路平安。",
            "你买下治疗药水，背包沉了一点。",
        ],
        "cmd": {"action": "buy", "target": "potion_red", "end_turn": "0"},
        "stats": {
            "hp": "90",
            "mp": "25",
            "loc": "杂货店",
            "quest": "找药草",
            "flags": "has_map,has_potion",
        },
        "abstracts": [
            "在杂货店买了红药；任务仍是找药草。",
        ],
    },
    {
        "tag": "cutscene_advance",
        # 压到极低：advance 易泄漏到 explore/flee
        "weight": 0.15,
        "user_texts": [
            "跳过过场动画。",
            "播放下一段过场。",
            "过场往后翻。",
        ],
        "fsm_in": {"phase": "cutscene", "node": "intro_1"},
        "thinks": [
            "输入 fsm.phase 已是 cutscene，才允许 action=advance；探索/战斗绝不能 advance。",
        ],
        "state": {
            "phase": "cutscene",
            "node": "intro_2",
            "allowed": "advance",
        },
        "says": [
            "画面淡入：远山之间，有人低声念着药草的名字。",
            "旁白响起：风暴将至，你必须在日落前找到那株叶子。",
        ],
        "cmd": {"action": "advance", "target": "intro_2", "end_turn": "0"},
        "stats": {
            "hp": "100",
            "mp": "30",
            "loc": "过场",
            "quest": "找药草",
            "flags": "intro",
        },
        "abstracts": [
            "过场推进到 intro_2；任务找药草尚未开始探索。",
        ],
    },
    {
        "tag": "combat_flee",
        "weight": 2.2,
        "user_texts": [
            "我跑！",
            "撤退。",
            "逃离战斗。",
            "逃跑。",
            "不想打了，跑！",
            "快逃。",
            "溜了溜了。",
            "我选择逃跑。",
        ],
        "fsm_in": {"phase": "combat", "node": "round_player"},
        "thinks": [
            "用户明确逃跑；phase: combat→explore；action=flee；end_turn=1；禁止 advance；禁止停留 combat。",
            "逃跑成功；切回 explore/cave_mouth；cmd 必须是 flee 且 end_turn=1。",
            "战斗中的 flee 转场：输出 phase=explore，绝不是 combat，也绝不是 advance。",
        ],
        "state": {
            "phase": "explore",
            "node": "cave_mouth",
            "allowed": "move,talk,open_inventory",
        },
        "says": [
            "你狼狈地退出战斗，回到洞口喘息。",
            "总算甩开了，心跳还很快。",
            "你转身狂奔，灰狼的吼声被甩在身后。",
            "你跌跌撞撞逃出交战，停在洞穴入口。",
            "逃出来了。战斗结束，你回到洞口。",
        ],
        "cmd": {"action": "flee", "target": "none", "end_turn": "1"},
        "stats": {
            "hp": "70",
            "mp": "15",
            "loc": "洞穴入口",
            "quest": "找药草",
            "flags": "has_map,fled_combat",
        },
        "abstracts": [
            "已逃离战斗回到洞穴入口；任务未完成。",
            "flee 成功；phase 已回 explore；人在洞穴入口。",
            "不在战斗中；刚从灰狼身边逃走；地点洞穴入口。",
        ],
    },
]


def render_quest_output(
    think: str,
    state: dict[str, str],
    say: str,
    cmd: dict[str, str],
    stats: dict[str, str],
    abstract: str,
) -> str:
    return (
        f"<think>\n{think}\n</think>\n\n"
        f"<state>\n{format_kv(state, order=['phase', 'node', 'allowed'])}\n</state>\n\n"
        f"<say>\n{say}\n</say>\n\n"
        f"<cmd>\n{format_kv(cmd, order=['action', 'target', 'end_turn'])}\n</cmd>\n\n"
        f"<stats>\n{format_kv(stats, order=['hp', 'mp', 'loc', 'quest', 'flags'])}\n</stats>\n\n"
        f"<abstract>\n{abstract}\n</abstract>"
    )


def _pick_text(sc: dict[str, Any], key_plural: str, key_singular: str, rng: random.Random) -> str:
    if key_plural in sc and sc[key_plural]:
        return rng.choice(sc[key_plural])
    return str(sc[key_singular])


def build_row(sc: dict[str, Any], rng: random.Random, index: int) -> dict[str, Any]:
    hp = int(sc["stats"]["hp"]) + rng.randint(-2, 2)
    mp = max(0, int(sc["stats"]["mp"]) + rng.randint(-1, 1))
    stats = dict(sc["stats"])
    stats["hp"] = str(max(1, hp))
    stats["mp"] = str(mp)
    say = _pick_text(sc, "says", "say", rng)
    user_text = rng.choice(sc["user_texts"])
    think = _pick_text(sc, "thinks", "think", rng)
    abstract = _pick_text(sc, "abstracts", "abstract", rng)
    out = render_quest_output(
        think=think,
        state=dict(sc["state"]),
        say=say,
        cmd=dict(sc["cmd"]),
        stats=stats,
        abstract=abstract,
    )
    return {
        "id": f"quest_syn_{index:04d}_{sc['tag']}",
        "input": {
            "user_text": user_text,
            "fsm": dict(sc["fsm_in"]),
            "stats": {
                "hp": stats["hp"],
                "mp": stats["mp"],
                "loc": stats["loc"],
                "quest": stats["quest"],
            },
        },
        "output": out,
        "meta": {"scenario": sc["tag"], "contract": "quest_v1"},
    }


def _weighted_choice(rng: random.Random) -> dict[str, Any]:
    weights = [float(sc.get("weight", 1.0)) for sc in SCENARIOS]
    return rng.choices(SCENARIOS, weights=weights, k=1)[0]


def generate_dataset(count: int, seed: int = 3407) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    rows: list[dict[str, Any]] = []
    # 每种场景至少一条，避免稀有转场被抽空
    for i, sc in enumerate(SCENARIOS):
        if len(rows) >= count:
            break
        rows.append(build_row(sc, random.Random(seed + i), i + 1))
    while len(rows) < count:
        idx = len(rows) + 1
        sc = _weighted_choice(rng)
        rows.append(build_row(sc, rng, idx))
    return rows[:count]


def split_train_val(
    rows: list[dict[str, Any]], val_ratio: float = 0.15, seed: int = 3407
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rng = random.Random(seed)
    shuffled = list(rows)
    rng.shuffle(shuffled)
    n_val = max(1, int(len(shuffled) * val_ratio))
    if n_val >= len(shuffled):
        n_val = max(1, len(shuffled) // 5)
    return shuffled[n_val:], shuffled[:n_val]
