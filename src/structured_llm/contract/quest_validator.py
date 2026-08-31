"""Quest RPG 回合校验。"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from .quest_parser import ParsedQuestTurn, try_parse_quest_turn

PHASES = frozenset({"explore", "combat", "dialogue", "shop", "cutscene"})
# 引擎侧指令（可不在 allowed 里）：allowed 只描述「下一拍玩家菜单」
ENGINE_ACTIONS = frozenset({"prompt_choice", "advance"})
PLAYER_ACTIONS = frozenset(
    {
        "move",
        "talk",
        "attack",
        "skill",
        "item",
        "flee",
        "buy",
        "open_inventory",
    }
)
ACTIONS = ENGINE_ACTIONS | PLAYER_ACTIONS

# 模型偶发英文/近义写法 → 合法枚举
ACTION_ALIASES = {
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

_STATE_REQUIRED = ("phase", "node", "allowed")
_CMD_REQUIRED = ("action", "end_turn")
_STATS_REQUIRED = ("hp", "mp", "loc", "quest", "flags")


@dataclass
class QuestValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    parsed: Optional[ParsedQuestTurn] = None

    def as_dict(self) -> dict[str, Any]:
        p = self.parsed
        return {
            "ok": self.ok,
            "errors": self.errors,
            "warnings": self.warnings,
            "parsed": None
            if p is None
            else {
                "think": p.think,
                "state": p.state,
                "say": p.say,
                "cmd": p.cmd,
                "stats": p.stats,
                "abstract": p.abstract,
            },
        }


def _int_field(name: str, raw: str, errors: list[str]) -> None:
    try:
        int(raw)
    except ValueError:
        errors.append(f"{name} 必须是整数：{raw!r}")


def validate_quest_turn(
    text: str,
    input_obj: Optional[dict[str, Any]] = None,
) -> QuestValidationResult:
    parsed, parse_error = try_parse_quest_turn(text)
    if parse_error:
        return QuestValidationResult(ok=False, errors=[parse_error])
    assert parsed is not None

    errors: list[str] = []
    warnings: list[str] = []

    for key in _STATE_REQUIRED:
        if key not in parsed.state:
            errors.append(f"state 缺少必填键：{key}")
    for key in _CMD_REQUIRED:
        if key not in parsed.cmd:
            errors.append(f"cmd 缺少必填键：{key}")
    for key in _STATS_REQUIRED:
        if key not in parsed.stats:
            errors.append(f"stats 缺少必填键：{key}")

    phase = parsed.state.get("phase")
    if phase and phase not in PHASES:
        errors.append(f"phase 非法：{phase}（允许 {sorted(PHASES)}）")

    action = parsed.cmd.get("action")
    if action and action in ACTION_ALIASES:
        parsed.cmd["action"] = ACTION_ALIASES[action]
        warnings.append(f"action 别名已归一：{action}→{parsed.cmd['action']}")
        action = parsed.cmd["action"]
    if action and action not in ACTIONS:
        errors.append(f"action 非法：{action}（允许 {sorted(ACTIONS)}）")

    end_turn = parsed.cmd.get("end_turn")
    if end_turn is not None and end_turn not in {"0", "1"}:
        errors.append("cmd.end_turn 必须是 0 或 1")

    allowed_raw = parsed.state.get("allowed", "")
    allowed = {x.strip() for x in allowed_raw.split(",") if x.strip()}
    # allowed = 本回合结束后玩家可选动作；cmd.action = 本步引擎/玩家已执行动作。
    # 切换 phase 时 action 常来自上一步菜单（如 flee→explore），不要求 action∈allowed。
    if action and action in PLAYER_ACTIONS and allowed and action not in allowed:
        warnings.append(
            f"action={action} 不在本拍 allowed={allowed_raw!r}（若为转场可忽略）"
        )
    if allowed and not allowed.issubset(ACTIONS):
        bad = sorted(allowed - ACTIONS)
        # 菜单项偶发幻觉不阻断整回合；phase/action 才是硬门禁
        warnings.append(f"state.allowed 含未知项：{bad}")

    if "hp" in parsed.stats:
        _int_field("stats.hp", parsed.stats["hp"], errors)
    if "mp" in parsed.stats:
        _int_field("stats.mp", parsed.stats["mp"], errors)

    if not parsed.say:
        errors.append("say 为空")
    elif re.search(r"</?(?:think|state|say|cmd|stats|abstract)\b", parsed.say, re.I):
        errors.append("say 不得嵌套结构标签")

    if not parsed.abstract:
        errors.append("abstract 为空")
    elif re.search(
        r"</?(?:think|state|say|cmd|stats|abstract)\b", parsed.abstract, re.I
    ):
        errors.append("abstract 不得嵌套结构标签")

    if not parsed.think:
        warnings.append("think 为空")
    if len(parsed.say) > 120:
        warnings.append("say 过长（>120 字）")
    if len(parsed.abstract) < 8:
        warnings.append("abstract 过短")

    # 可选：输入侧 phase 与输出不一致时仅提示（遇敌/逃跑等转场是正常的）
    if isinstance(input_obj, dict):
        hint = (input_obj.get("fsm") or {}).get("phase")
        if hint and phase and hint != phase:
            warnings.append(f"phase 转场：{hint} → {phase}")

    return QuestValidationResult(
        ok=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        parsed=parsed,
    )
