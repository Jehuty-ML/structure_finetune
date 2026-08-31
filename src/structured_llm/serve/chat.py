"""真机对话回合：生成 → 契约解析 → 假 TTS / 假引擎。"""

from __future__ import annotations

from typing import Any, Callable, Optional

from structured_llm.data import format_user_message
from structured_llm.serve.response import (
    fake_engine_consume,
    fake_tts_consume,
    parse_generation_to_response,
    parse_quest_generation_to_response,
)


def build_user_input(
    user_text: str,
    *,
    turn: int,
    can_speak: bool,
    user_emotion: str = "neutral",
) -> dict[str, Any]:
    return {
        "user_text": user_text,
        "user_emotion": user_emotion,
        "session": {"energy": 55, "bond": 4, "turn": turn},
        "device": {"can_speak": can_speak, "interruptible": can_speak},
    }


def guess_emotion(user_text: str) -> str:
    t = user_text
    if any(k in t for k in ("累", "疲惫", "睡着")):
        return "tired"
    if any(k in t for k in ("开心", "升职", "恭喜", "太棒")):
        return "happy"
    if any(k in t for k in ("不安", "紧张", "悬着", "搬")):
        return "anxious"
    if any(k in t for k in ("朋友", "难过", "糟")):
        return "sad"
    return "neutral"


def should_force_mute(user_text: str) -> bool:
    return any(
        k in user_text for k in ("图书馆", "静音", "别出声", "只回文字", "开会中")
    )


def run_echo_turn(
    *,
    user_text: str,
    generate_fn: Callable[[str, str], str],
    system_prompt: str,
    schema_path: str,
    history: list[tuple[str, str]],
    turn: int,
    can_speak: bool,
    user_emotion: Optional[str] = None,
) -> dict[str, Any]:
    speak = can_speak
    if should_force_mute(user_text):
        speak = False

    emotion = user_emotion or guess_emotion(user_text)
    inp = build_user_input(
        user_text, turn=turn, can_speak=speak, user_emotion=emotion
    )
    # 与训练 / evaluate 一致：只传助手口播 Prior，避免格式漂移
    prior_utters = [a for _, a in history]
    user_msg = format_user_message(inp, prior_utters if prior_utters else None)
    raw = generate_fn(system_prompt, user_msg)
    resp = parse_generation_to_response(
        raw, schema_path=schema_path, input_obj=inp
    )
    out: dict[str, Any] = {
        "ok": bool(resp.get("ok")),
        "input": inp,
        "raw": raw,
        "think": resp.get("think"),
        "voice": resp.get("voice"),
        "tts": None,
        "errors": resp.get("errors") or [],
        "warnings": resp.get("warnings") or [],
        "can_speak": speak,
        "history": list(history),
    }
    if out["ok"] and out["voice"]:
        out["tts"] = fake_tts_consume(out["voice"])
        out["tts_log"] = fake_tts_consume(out["voice"], as_log_line=True)
        utter = str(out["voice"].get("utter") or "")
        out["history"] = history + [(user_text, utter)]
    return out


def build_quest_input(
    user_text: str,
    *,
    fsm: dict[str, str],
    stats: dict[str, str],
) -> dict[str, Any]:
    """Quest 用户侧 JSON：与合成数据 / system prompt 对齐。"""
    return {
        "user_text": user_text,
        "fsm": {
            "phase": str(fsm.get("phase", "explore")),
            "node": str(fsm.get("node", "start")),
        },
        "stats": {
            "hp": str(stats.get("hp", "80")),
            "mp": str(stats.get("mp", "20")),
            "loc": str(stats.get("loc", "未知")),
            "quest": str(stats.get("quest", "")),
        },
    }


_ENCOUNTER_KEYS = (
    "狼",
    "怪物",
    "遇敌",
    "开战",
    "战斗开始",
    "伏击",
    "敌袭",
    "敌对",
    "野兽",
    "扑过来",
    "挡住",
    "咬我",
    "打怪",
    "打怪物",
    "杀怪",
    "干它",
)
_FLEE_KEYS = ("跑", "逃", "撤退", "撤离", "溜了", "不打了")
_ATTACK_KEYS = (
    "攻击",
    "砍",
    "打",
    "挥剑",
    "刺",
    "平A",
    "普攻",
    "斩",
    "冷冻",
    "火焰",
    "毒针",
    "冰锥",
    "光刃",
    "技能",
    "砸",
    "拳",
    "箭",
)


_DIR_EAST = ("东侧", "向东", "走东", "东边", "右边", "右侧", "我选东", "探东")
_DIR_WEST = ("西侧", "向西", "走西", "西边", "左边", "左侧", "密林", "我选西")
_DIR_SOUTH = ("南边", "向南", "走南", "南侧")
_DIR_NORTH = ("北边", "向北", "走北", "北侧")
_DIR_CAVE = ("进洞", "洞口", "往洞", "入洞", "探洞")
_DIR_BACK = ("回原路", "原路", "退后", "返回路口", "回岔口", "回路口")
_FORWARD_KEYS = (
    "继续",
    "向前",
    "往前",
    "深入",
    "再走",
    "接着走",
    "沿药",
    "跟着味",
    "顺着味",
    "药草味",
    "药香",
    "靠近洞",
    "靠近石壁",
    "过去",
    "再往前",
)


def _direction_destination(user_text: str) -> dict[str, str] | None:
    """若玩家在选方向，返回 node/target/loc/say/abstract；否则 None。"""
    t = user_text or ""
    # 遇敌优先，不走位移
    if any(k in t for k in _ENCOUNTER_KEYS):
        return None
    if any(k in t for k in _DIR_CAVE):
        return {
            "node": "cave_mouth",
            "target": "cave_mouth",
            "loc": "洞穴入口",
            "say": "你离开岔口，走到洞穴入口。洞风发凉，地上有干草屑，药草味若有若无。",
            "abstract": "已推进到洞穴入口；离开森林路口。",
        }
    if any(k in t for k in _DIR_EAST) or t.strip() in {"东", "右"}:
        return {
            "node": "east_trail",
            "target": "east_trail",
            "loc": "东侧树丛小径",
            "say": "你拨开东侧矮树丛往前走。药草清香更浓了，前方隐约可见洞口石壁。",
            "abstract": "已离开岔口，抵达东侧树丛小径；药草气味变浓。",
        }
    if any(k in t for k in _DIR_WEST) or t.strip() in {"西", "左"}:
        return {
            "node": "west_thicket",
            "target": "west_thicket",
            "loc": "西侧密林边缘",
            "say": "你钻进西侧密林。光线暗下来，树干上有爪痕，但你还没被扑上。",
            "abstract": "已西行至密林边缘；离开森林路口。",
        }
    if any(k in t for k in _DIR_SOUTH) or t.strip() in {"南"}:
        return {
            "node": "dry_creek",
            "target": "dry_creek",
            "loc": "枯溪浅滩",
            "say": "你往南走下坡，岔口被甩在身后。坡底枯溪对岸有浅滩，岸边长着带露嫩叶。",
            "abstract": "已南行至枯溪浅滩；离开森林路口。",
        }
    if any(k in t for k in _DIR_NORTH) or t.strip() in {"北"}:
        return {
            "node": "north_ridge",
            "target": "north_ridge",
            "loc": "北向山脊小道",
            "say": "你向北登上狭窄山脊。视野开阔，能看见远处洞口冒出的薄雾。",
            "abstract": "已北行至山脊小道；离开森林路口。",
        }
    if any(k in t for k in _DIR_BACK):
        return {
            "node": "forest_fork",
            "target": "forest_fork",
            "loc": "森林路口",
            "say": "你退回森林路口。东侧树丛、西侧密林，或往洞口走，请再选。",
            "abstract": "已退回森林路口；等待选路。",
        }
    return None


# 当前节点上说「继续/向前」时，推进到下一地点（打破原地 prompt_choice 死循环）
_NODE_FORWARD: dict[str, dict[str, str]] = {
    "east_trail": {
        "node": "cave_mouth",
        "target": "cave_mouth",
        "loc": "洞穴入口",
        "say": "你顺着药香继续向前，树丛尽头是洞穴入口。洞风发凉，石壁渗水。",
        "abstract": "沿东径抵达洞穴入口；药香更近。",
    },
    "west_thicket": {
        "node": "cave_mouth",
        "target": "cave_mouth",
        "loc": "洞穴入口",
        "say": "你穿过密林侧径，绕到洞穴入口一侧。爪痕到此变密，但暂无狼影。",
        "abstract": "由密林绕至洞穴入口。",
    },
    "dry_creek": {
        "node": "cave_mouth",
        "target": "cave_mouth",
        "loc": "洞穴入口",
        "say": "你沿枯溪上行，浅滩尽头接到洞穴入口砂地。",
        "abstract": "由枯溪抵达洞穴入口。",
    },
    "north_ridge": {
        "node": "cave_mouth",
        "target": "cave_mouth",
        "loc": "洞穴入口",
        "say": "你沿山脊下行，薄雾散处正是洞穴入口。",
        "abstract": "由山脊抵达洞穴入口。",
    },
    "trail_marker": {
        "node": "forest_fork",
        "target": "forest_fork",
        "loc": "森林路口",
        "say": "你离开标记点，再次站在森林路口。东、西、洞口，请选。",
        "abstract": "回森林路口；等待选路。",
    },
    "cave_mouth": {
        "node": "herb_nook",
        "target": "herb_nook",
        "loc": "洞口药草凹坑",
        "say": "你在洞口石缝找到一小丛药草，清香扑鼻。可采摘，也可再进洞探。",
        "abstract": "洞口找到药草凹坑；任务接近完成。",
    },
    "herb_nook": {
        "node": "herb_nook",
        "target": "herb_nook",
        "loc": "洞口药草凹坑",
        "say": "药草已在手边。输入「采药」收下，或「进洞」继续探查。",
        "abstract": "停在药草凹坑；可采药或进洞。",
    },
}


def _wants_forward(user_text: str) -> bool:
    t = (user_text or "").strip()
    if not t:
        return False
    return any(k in t for k in _FORWARD_KEYS)


def _apply_move_dest(
    *,
    dest: dict[str, str],
    state: dict[str, Any],
    cmd: dict[str, Any],
    stats: dict[str, Any] | None,
    patches: dict[str, Any],
) -> None:
    state["phase"] = "explore"
    state["node"] = dest["node"]
    state["allowed"] = "move,talk,open_inventory"
    cmd["action"] = "move"
    cmd["target"] = dest["target"]
    cmd["end_turn"] = "0"
    if stats is not None:
        stats["loc"] = dest["loc"]
    patches["say"] = dest["say"]
    patches["abstract"] = dest["abstract"]


def _explore_menu_for_node(node: str, loc: str) -> tuple[str, str]:
    """按当前地点给出选路提示，禁止错说成还在森林路口。"""
    if node in {"east_trail"}:
        return (
            f"你还在{loc or '东侧树丛小径'}。可输入「继续向前」去洞口，或「回路口」。",
            "仍在东侧小径；等待继续或返回。",
        )
    if node in {"west_thicket"}:
        return (
            f"你还在{loc or '西侧密林'}。可「继续向前」绕到洞口，或「回路口」。",
            "仍在密林；等待继续或返回。",
        )
    if node in {"cave_mouth"}:
        return (
            f"你在{loc or '洞穴入口'}。可「继续」找药草，或留意是否有狼。",
            "停在洞穴入口；等待行动。",
        )
    if node in {"herb_nook"}:
        return (
            "药草就在眼前。输入「采药」或「进洞」。",
            "停在药草凹坑。",
        )
    return (
        f"你在{loc or '森林路口'}。请选择：东侧树丛、西侧密林、或往洞口走。",
        "仍在岔口；等待选路。",
    )


_GREET_KEYS = ("你好", "您好", "在吗", "hello", "hi", "哈喽", "嗨")
_COMBAT_MENU = {
    "1": "attack",
    "2": "skill",
    "3": "item",
    "4": "flee",
}
_PICK_HERB_KEYS = ("采药", "采草", "摘药", "收药", "拔草", "拿走药草")


def _is_explore_noise(user_text: str) -> bool:
    """探索阶段无明确意图：空、纯数字、纯问候。不把「继续」当噪声。"""
    t = (user_text or "").strip()
    if not t:
        return True
    if t.isdigit():
        return True
    low = t.lower()
    if low in {x.lower() for x in _GREET_KEYS}:
        return True
    if t in _GREET_KEYS:
        return True
    # 单字乱按，但不拦截东/西/南/北等
    if len(t) == 1 and t not in {"东", "西", "南", "北", "左", "右", "洞"}:
        return True
    return False


def repair_quest_fields(
    *,
    user_text: str,
    fsm_in: dict[str, str],
    state: dict[str, Any],
    cmd: dict[str, Any],
    stats: dict[str, Any] | None = None,
    patches: dict[str, Any] | None = None,
    model_say: str = "",
) -> list[str]:
    """
    引擎侧轻量修补：小模型偶发写错 phase 时，用意图关键词 + 输入 fsm 纠正。
    patches 可写入 say/abstract 覆盖（用于选方向推进）。
    """
    notes: list[str] = []
    phase_in = str(fsm_in.get("phase", ""))
    node_in = str(fsm_in.get("node") or "forest_fork")
    action = str(cmd.get("action") or "")
    t = user_text or ""
    patches = patches if patches is not None else {}
    say_hint = str(model_say or patches.get("say") or "")
    loc_in = str((stats or {}).get("loc") or "")

    # 修正非法 allowed
    allowed = str(state.get("allowed") or "")
    if "cargo_inventory" in allowed:
        state["allowed"] = allowed.replace("cargo_inventory", "open_inventory")
        notes.append("repair: allowed cargo_inventory→open_inventory")
    if "prompt_choice" in allowed and phase_in == "explore":
        # explore allowed 契约通常不含 prompt_choice 字面；去掉以免脏状态
        parts = [p for p in allowed.split(",") if p and p != "prompt_choice"]
        state["allowed"] = ",".join(parts) or "move,talk,open_inventory"

    # 动作别名
    _ACTION_ALIAS = {
        "movement": "move",
        "walk": "move",
        "go": "move",
        "hit": "attack",
        "strike": "attack",
        "run": "flee",
        "escape": "flee",
        "retreat": "flee",
        "fled": "flee",
        "choice": "prompt_choice",
        "choose": "prompt_choice",
        "select": "prompt_choice",
    }
    if action in _ACTION_ALIAS:
        cmd["action"] = _ACTION_ALIAS[action]
        notes.append(f"repair: action {action}→{cmd['action']}")
        action = str(cmd["action"])

    # —— 探索 ——
    if phase_in == "explore":
        # 遇敌
        if any(k in t for k in _ENCOUNTER_KEYS):
            state["phase"] = "combat"
            state["node"] = "round_player"
            state["allowed"] = "attack,skill,item,flee"
            cmd["action"] = "prompt_choice"
            cmd["target"] = "combat_menu"
            cmd["end_turn"] = "0"
            patches["say"] = (
                "灰狼挡住去路，低吼逼近。战斗开始：输入 1攻击 2技能 3道具 4逃跑。"
            )
            patches["abstract"] = "遇敌开战；玩家选行动。"
            notes.append("repair: explore遇敌→combat菜单")
            return notes

        # 洞口采药
        if node_in in {"cave_mouth", "herb_nook"} and any(
            k in t for k in _PICK_HERB_KEYS
        ):
            state["phase"] = "explore"
            state["node"] = "herb_nook"
            state["allowed"] = "move,talk,open_inventory"
            cmd["action"] = "move"
            cmd["target"] = "herb_nook"
            cmd["end_turn"] = "0"
            if stats is not None:
                stats["loc"] = "洞口药草凹坑"
                flags = str(stats.get("flags") or "has_map")
                if "got_herb" not in flags:
                    stats["flags"] = flags + ",got_herb"
            patches["say"] = "你采下一簇带露药草，清香入鼻。任务「找药草」可回报了。"
            patches["abstract"] = "已采集药草；任务可完成。"
            notes.append("repair: 采药→herb_nook")
            return notes

        # 显式选方向（东/西/洞…）
        dest = _direction_destination(t)
        if dest is not None:
            _apply_move_dest(
                dest=dest, state=state, cmd=cmd, stats=stats, patches=patches
            )
            notes.append(f"repair: 选方向→move@{dest['node']}")
            return notes

        # 「继续/向前/沿药香」：按当前节点推进，禁止原地假移动
        if _wants_forward(t):
            if node_in in {"forest_fork", "start", ""}:
                say, abs_ = _explore_menu_for_node("forest_fork", loc_in or "森林路口")
                state["phase"] = "explore"
                state["node"] = "forest_fork"
                state["allowed"] = "move,talk,open_inventory"
                cmd["action"] = "prompt_choice"
                cmd["target"] = "cave_entrance"
                cmd["end_turn"] = "0"
                patches["say"] = "还在岔口，请先选方向：东侧树丛、西侧密林、或往洞口。"
                patches["abstract"] = abs_
                notes.append("repair: 岔口说继续→先选方向")
                return notes
            fwd = _NODE_FORWARD.get(node_in)
            if fwd is not None:
                _apply_move_dest(
                    dest=fwd, state=state, cmd=cmd, stats=stats, patches=patches
                )
                notes.append(f"repair: 继续向前→move@{fwd['node']}")
                return notes

        # 仅当模型无端跳进战斗/非法战斗动作时，拉回当前地点菜单（不硬改回森林路口文案）
        rogue_combat = state.get("phase") == "combat" or action in {
            "attack",
            "skill",
            "item",
            "flee",
        }
        if rogue_combat or _is_explore_noise(t):
            state["phase"] = "explore"
            node = node_in if node_in not in {
                "round_player",
                "round_enemy",
                "enemy_round",
            } else "forest_fork"
            state["node"] = node
            state["allowed"] = "move,talk,open_inventory"
            cmd["action"] = "prompt_choice"
            cmd["target"] = "cave_entrance"
            cmd["end_turn"] = "0"
            say, abs_ = _explore_menu_for_node(node, loc_in)
            if any(k in t for k in _GREET_KEYS) or t.strip().lower() in {"hello", "hi"}:
                patches["say"] = f"你好。{say}"
            else:
                patches["say"] = say
            patches["abstract"] = abs_
            notes.append("repair: 探索纠偏→当前地点菜单")
            return notes

        # 模型写了 move 但 node/loc 没变：若说了继续，上面已处理；这里修同地假 move
        if (
            action == "move"
            and str(state.get("node") or "") == node_in
            and node_in in _NODE_FORWARD
            and _wants_forward(t)
        ):
            fwd = _NODE_FORWARD[node_in]
            _apply_move_dest(
                dest=fwd, state=state, cmd=cmd, stats=stats, patches=patches
            )
            notes.append(f"repair: 同地假move→推进@{fwd['node']}")
            return notes

    # —— 战斗 ——
    if phase_in == "combat":
        key = t.strip()
        # 数字菜单：1攻击 2技能 3道具 4逃跑
        if key in _COMBAT_MENU:
            mapped = _COMBAT_MENU[key]
            if mapped == "attack":
                state["phase"] = "combat"
                state["node"] = "round_player"
                state["allowed"] = "attack,skill,item,flee"
                cmd["action"] = "attack"
                cmd["target"] = "wolf"
                cmd["end_turn"] = "0"
                notes.append("repair: 菜单1→attack")
                return notes
            if mapped == "flee":
                state["phase"] = "explore"
                state["node"] = "cave_mouth"
                state["allowed"] = "move,talk,open_inventory"
                cmd["action"] = "flee"
                cmd["target"] = "none"
                cmd["end_turn"] = "1"
                patches["say"] = "你退出战斗，回到洞穴入口喘息。"
                patches["abstract"] = "已逃离战斗；回到洞穴入口。"
                notes.append("repair: 菜单4→flee")
                return notes
            # skill / item 未实装：只给菜单
            state["phase"] = "combat"
            state["node"] = "round_player"
            state["allowed"] = "attack,skill,item,flee"
            cmd["action"] = "prompt_choice"
            cmd["target"] = "combat_menu"
            cmd["end_turn"] = "0"
            patches["say"] = f"选项{key}尚未实装。请输入 1攻击 或 4逃跑。"
            patches["abstract"] = "战斗中；等待有效行动。"
            notes.append(f"repair: 菜单{key}未实装→提示")
            return notes

        if any(k in t for k in _FLEE_KEYS):
            state["phase"] = "explore"
            state["node"] = "cave_mouth"
            state["allowed"] = "move,talk,open_inventory"
            cmd["action"] = "flee"
            cmd["target"] = "none"
            cmd["end_turn"] = "1"
            notes.append("repair: 逃跑用语→flee")
            return notes

        if any(k in t for k in _ATTACK_KEYS):
            state["phase"] = "combat"
            state["node"] = "round_player"
            state["allowed"] = "attack,skill,item,flee"
            cmd["action"] = "attack"
            if cmd.get("target") in {None, "", "cave_entrance", "combat_menu"}:
                cmd["target"] = "wolf"
            cmd["end_turn"] = "0"
            notes.append("repair: 攻击用语→attack")
            return notes

        # 问候/纯数字：弹出战斗菜单，禁止乱 flee
        if _is_explore_noise(t) or any(k in t for k in _GREET_KEYS):
            state["phase"] = "combat"
            state["node"] = "round_player"
            state["allowed"] = "attack,skill,item,flee"
            cmd["action"] = "prompt_choice"
            cmd["target"] = "combat_menu"
            cmd["end_turn"] = "0"
            patches["say"] = "战斗还在继续。请输入：1攻击 2技能 3道具 4逃跑。"
            patches["abstract"] = "战斗中；等待菜单选择。"
            notes.append("repair: 战斗中无效输入→菜单")
            return notes

        # 模型把攻击旁白配成 prompt_choice：若旁白像攻击则改回 attack
        if action == "prompt_choice" and (
            "造成" in say_hint or "点伤害" in say_hint
        ):
            cmd["action"] = "attack"
            cmd["target"] = "wolf"
            cmd["end_turn"] = "0"
            notes.append("repair: 攻击旁白配错prompt_choice→attack")

    return notes


def run_quest_turn(
    *,
    user_text: str,
    generate_fn: Callable[[str, str], str],
    system_prompt: str,
    fsm: dict[str, str],
    stats: dict[str, str],
    history: list[tuple[str, str]],
) -> dict[str, Any]:
    """
    Quest 真机一回合。

    history 存 (user_text, abstract)；与训练一致用 Abstract 行作 Prior。
    成功时用输出 state/stats 更新会话，供下一轮输入。
    """
    inp = build_quest_input(user_text, fsm=fsm, stats=stats)
    prior_abstracts = [a for _, a in history]
    user_msg = format_user_message(
        inp,
        prior_abstracts if prior_abstracts else None,
        prior_label="Abstract",
    )
    raw = generate_fn(system_prompt, user_msg)
    resp = parse_quest_generation_to_response(raw, input_obj=inp)
    out: dict[str, Any] = {
        "ok": bool(resp.get("ok")),
        "input": inp,
        "raw": raw,
        "think": resp.get("think"),
        "state": resp.get("state"),
        "say": resp.get("say"),
        "cmd": resp.get("cmd"),
        "stats": resp.get("stats"),
        "abstract": resp.get("abstract"),
        "engine": None,
        "errors": resp.get("errors") or [],
        "warnings": list(resp.get("warnings") or []),
        "history": list(history),
        "fsm": dict(fsm),
        "session_stats": dict(stats),
    }
    if out["ok"] and out["state"] and out["cmd"] and out["stats"] is not None:
        patches: dict[str, Any] = {}
        notes = repair_quest_fields(
            user_text=user_text,
            fsm_in=fsm,
            state=out["state"],
            cmd=out["cmd"],
            stats=out["stats"],
            patches=patches,
            model_say=str(out.get("say") or ""),
        )
        if notes:
            out["warnings"].extend(notes)
        if patches.get("say"):
            out["say"] = patches["say"]
        if patches.get("abstract"):
            out["abstract"] = patches["abstract"]
        out["engine"] = fake_engine_consume(
            state=out["state"],
            say=str(out["say"] or ""),
            cmd=out["cmd"],
            stats=out["stats"],
        )
        out["engine_log"] = fake_engine_consume(
            state=out["state"],
            say=str(out["say"] or ""),
            cmd=out["cmd"],
            stats=out["stats"],
            as_log_line=True,
        )
        # 下一拍输入：输出 state → fsm；输出 stats → session
        out["fsm"] = {
            "phase": str(out["state"].get("phase", fsm.get("phase", "explore"))),
            "node": str(out["state"].get("node", fsm.get("node", "start"))),
        }
        out["session_stats"] = {
            "hp": str(out["stats"].get("hp", stats.get("hp", "80"))),
            "mp": str(out["stats"].get("mp", stats.get("mp", "20"))),
            "loc": str(out["stats"].get("loc", stats.get("loc", "未知"))),
            "quest": str(out["stats"].get("quest", stats.get("quest", ""))),
        }
        abstract = str(out.get("abstract") or "")
        out["history"] = history + [(user_text, abstract)]
    return out
