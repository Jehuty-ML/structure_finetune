"""Quest 数据组装：规则卡 + 改写文案（非排列组合抽奖）。

设计：
1) examples/quest/rules/*.yaml  — 决策标签（fsm_in / assert）
2) examples/quest/rewrites/*.json — 每卡独立 user_text/say/...
3) 每个 user_text 只生成一行；全局 user_text 不得跨卡重复
4) train/val 按 user_text 留出，避免同源泄漏
"""

from __future__ import annotations

import json
import hashlib
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from structured_llm.contract.kv import format_kv
from structured_llm.contract.quest_validator import validate_quest_turn

ROOT_DEFAULT = Path(__file__).resolve().parents[3]
RULES_DIR_DEFAULT = ROOT_DEFAULT / "examples" / "quest" / "rules"
REWRITES_DIR_DEFAULT = ROOT_DEFAULT / "examples" / "quest" / "rewrites"


@dataclass(frozen=True)
class RuleCard:
    id: str
    fsm_in: dict[str, str]
    assert_fields: dict[str, str]
    stats_base: dict[str, str]
    repeat: int = 1


@dataclass(frozen=True)
class RewriteBank:
    rule_id: str
    user_texts: list[str]
    thinks: list[str]
    says: list[str]
    abstracts: list[str]


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise ImportError("需要 PyYAML：pip install pyyaml") from exc
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"规则卡必须是 mapping：{path}")
    return data


def load_rule_cards(rules_dir: str | Path | None = None) -> list[RuleCard]:
    d = Path(rules_dir) if rules_dir else RULES_DIR_DEFAULT
    cards: list[RuleCard] = []
    for path in sorted(d.glob("*.yaml")):
        raw = _load_yaml(path)
        cards.append(
            RuleCard(
                id=str(raw["id"]),
                fsm_in={k: str(v) for k, v in dict(raw["fsm_in"]).items()},
                assert_fields={k: str(v) for k, v in dict(raw["assert"]).items()},
                stats_base={k: str(v) for k, v in dict(raw["stats_base"]).items()},
                repeat=max(1, int(raw.get("repeat", 1))),
            )
        )
    if not cards:
        raise FileNotFoundError(f"未找到规则卡：{d}")
    return cards


def load_rewrite_banks(rewrites_dir: str | Path | None = None) -> dict[str, RewriteBank]:
    d = Path(rewrites_dir) if rewrites_dir else REWRITES_DIR_DEFAULT
    banks: dict[str, RewriteBank] = {}
    for path in sorted(d.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        rid = str(raw["rule_id"])
        users = [str(x).strip() for x in raw.get("user_texts", []) if str(x).strip()]
        thinks = [str(x).strip() for x in raw.get("thinks", []) if str(x).strip()]
        says = [str(x).strip() for x in raw.get("says", []) if str(x).strip()]
        abstracts = [str(x).strip() for x in raw.get("abstracts", []) if str(x).strip()]
        if not users or not thinks or not says or not abstracts:
            raise ValueError(f"改写库字段不完整：{path}")
        # 卡内 user_text 去重，保序
        seen: set[str] = set()
        uniq_users: list[str] = []
        for u in users:
            if u not in seen:
                seen.add(u)
                uniq_users.append(u)
        banks[rid] = RewriteBank(
            rule_id=rid,
            user_texts=uniq_users,
            thinks=thinks,
            says=says,
            abstracts=abstracts,
        )
    return banks


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


def _pick(_rng: random.Random, items: list[str], salt: str) -> str:
    h = int(hashlib.md5(salt.encode("utf-8")).hexdigest(), 16)
    return items[h % len(items)]


def _jitter_stats(base: dict[str, str], rng: random.Random) -> dict[str, str]:
    stats = dict(base)
    try:
        hp = int(stats.get("hp", "80")) + rng.randint(-2, 2)
        mp = max(0, int(stats.get("mp", "20")) + rng.randint(-1, 1))
        stats["hp"] = str(max(1, hp))
        stats["mp"] = str(mp)
    except ValueError:
        pass
    return stats


def _assert_matches_card(row: dict[str, Any], card: RuleCard) -> list[str]:
    problems: list[str] = []
    vr = validate_quest_turn(row["output"], input_obj=row.get("input"))
    if not vr.ok:
        return list(vr.errors)
    assert vr.parsed is not None
    af = card.assert_fields
    mapping = {
        "phase": vr.parsed.state.get("phase"),
        "node": vr.parsed.state.get("node"),
        "allowed": vr.parsed.state.get("allowed"),
        "action": vr.parsed.cmd.get("action"),
        "target": vr.parsed.cmd.get("target"),
        "end_turn": vr.parsed.cmd.get("end_turn"),
    }
    for key, expect in af.items():
        got = mapping.get(key)
        if got != expect:
            problems.append(f"{card.id} 字段 {key}={got!r} != {expect!r}")
    return problems


def assemble_dataset(
    *,
    rules_dir: str | Path | None = None,
    rewrites_dir: str | Path | None = None,
    seed: int = 3407,
    max_per_rule: int | None = None,
) -> list[dict[str, Any]]:
    cards = load_rule_cards(rules_dir)
    banks = load_rewrite_banks(rewrites_dir)
    missing = [c.id for c in cards if c.id not in banks]
    if missing:
        raise FileNotFoundError(f"缺少改写库：{missing}")

    # 全局 user_text 不得跨卡重复
    owner: dict[str, str] = {}
    for card in cards:
        for u in banks[card.id].user_texts:
            if u in owner and owner[u] != card.id:
                raise ValueError(
                    f"user_text 跨卡重复：{u!r} 同时属于 {owner[u]} 与 {card.id}"
                )
            owner[u] = card.id

    rows: list[dict[str, Any]] = []
    idx = 0
    for card in cards:
        bank = banks[card.id]
        users = list(bank.user_texts)
        if max_per_rule is not None:
            users = users[: max(1, max_per_rule)]
        for rep in range(card.repeat):
            for user_text in users:
                idx += 1
                rng = random.Random(f"{seed}:{card.id}:{rep}:{user_text}")
                think = _pick(rng, bank.thinks, f"t:{rep}:{user_text}")
                say = _pick(rng, bank.says, f"s:{rep}:{user_text}")
                abstract = _pick(rng, bank.abstracts, f"a:{rep}:{user_text}")
                stats = _jitter_stats(card.stats_base, rng)
                state = {
                    "phase": card.assert_fields["phase"],
                    "node": card.assert_fields["node"],
                    "allowed": card.assert_fields["allowed"],
                }
                cmd = {
                    "action": card.assert_fields["action"],
                    "target": card.assert_fields.get("target", "none"),
                    "end_turn": card.assert_fields["end_turn"],
                }
                out = render_quest_output(think, state, say, cmd, stats, abstract)
                row = {
                    "id": f"quest_{card.id}_{idx:04d}",
                    "input": {
                        "user_text": user_text,
                        "fsm": dict(card.fsm_in),
                        "stats": {
                            "hp": stats["hp"],
                            "mp": stats["mp"],
                            "loc": stats["loc"],
                            "quest": stats["quest"],
                        },
                    },
                    "output": out,
                    "meta": {
                        "scenario": card.id,
                        "contract": "quest_v2_rules",
                        "rule_id": card.id,
                        "repeat": rep,
                    },
                }
                problems = _assert_matches_card(row, card)
                if problems:
                    raise ValueError(f"组装失败 {row['id']}: {problems}")
                rows.append(row)
    return rows


def generate_dataset(
    count: int | None = None,
    seed: int = 3407,
    *,
    rules_dir: str | Path | None = None,
    rewrites_dir: str | Path | None = None,
) -> list[dict[str, Any]]:
    """兼容旧入口：count 表示每卡最多取多少条 user_text；None=全量。"""
    max_per_rule = count
    return assemble_dataset(
        rules_dir=rules_dir,
        rewrites_dir=rewrites_dir,
        seed=seed,
        max_per_rule=max_per_rule,
    )


def split_train_val(
    rows: list[dict[str, Any]], val_ratio: float = 0.15, seed: int = 3407
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """按 user_text 留出验证集（同一说法不会同时出现在 train/val）。"""
    rng = random.Random(seed)
    by_user: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        u = str(row["input"]["user_text"])
        by_user.setdefault(u, []).append(row)
    users = list(by_user.keys())
    rng.shuffle(users)
    n_val = max(1, int(len(users) * val_ratio))
    if n_val >= len(users):
        n_val = max(1, len(users) // 5)
    val_users = set(users[:n_val])
    train: list[dict[str, Any]] = []
    val: list[dict[str, Any]] = []
    for u, group in by_user.items():
        (val if u in val_users else train).extend(group)
    rng.shuffle(train)
    rng.shuffle(val)
    return train, val


def dataset_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    from collections import Counter

    return {
        "n": len(rows),
        "unique_user": len({r["input"]["user_text"] for r in rows}),
        "by_rule": dict(Counter(r["meta"]["rule_id"] for r in rows)),
    }
