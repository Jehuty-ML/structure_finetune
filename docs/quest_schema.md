# Quest（Ember）输出契约

虚构文字 RPG 回合。与 Echo 不同：**无整包 JSON**，全部用分块 + `key=value`。

块顺序（必须）：

1. `<think>` — 可剥离  
2. `<state>` — **状态机**（phase / node / allowed）  
3. `<say>` — 玩家可见旁白  
4. `<cmd>` — 引擎本步指令  
5. `<stats>` — 角色/世界快照（hp 等，**不是** FSM）  
6. `<abstract>` — 下一轮压缩记忆  

## 示例

```text
<think>
探索阶段，路口可前进；保持 explore。
</think>

<state>
phase=explore; node=forest_fork; allowed=move,talk,open_inventory
</state>

<say>
这条路通向山洞。要进去吗？
</say>

<cmd>
action=prompt_choice; target=cave_entrance; end_turn=0
</cmd>

<stats>
hp=80; mp=20; loc=森林路口; quest=找药草; flags=has_map
</stats>

<abstract>
探索中停在森林路口；任务找药草；已有地图；未进洞。
</abstract>
```

## 枚举

- `phase`：`explore` | `combat` | `dialogue` | `shop` | `cutscene`  
- `action`：`move` | `talk` | `attack` | `skill` | `item` | `flee` | `buy` | `prompt_choice` | `open_inventory` | `advance`  
- `end_turn`：`0` | `1`  

语义：

- `state.allowed`：本回合结束后的**玩家菜单**（逗号分隔）  
- `cmd.action`：本步已执行的引擎/玩家动作（可为 `prompt_choice` 等，不必 ∈ allowed）  
- 转场回合（如 `flee` → `explore`）不要求 `action ∈ allowed`

实现：`structured_llm.contract.quest_parser` / `quest_validator`。

## 数据（v2：规则卡 + 改写）

不再用大字典加权抽奖。当前流水线：

1. `examples/quest/rules/*.yaml` — 决策标签（`fsm_in` + `assert`）  
2. `examples/quest/rewrites/*.json` — 每卡独立、去重的 `user_text` / `say` / …  
3. `scripts/generate_quest_data.py` — 组装、字段断言、**按 user_text 留出 val**

```bash
python scripts/generate_quest_data.py
python scripts/validate_data.py --contract quest --data examples/quest/sample_data/train.json
python scripts/train.py --config examples/quest/configs/sft_lora.yaml
```

首版只覆盖四卡：`explore_fork` / `combat_start` / `combat_attack` / `combat_flee`（不含 `advance`）。

评测 / 聊天：`evaluate.py --contract quest` · `scripts/chat_quest.py`。
