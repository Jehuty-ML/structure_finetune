# Echo 数据质量规范（契约 v3）

> 本规范约束 **合成 / 标注数据** 与模型生成结果。训练入库前必须全部通过硬失败检查。

校验入口：`python scripts/validate_data.py --data <path>`  
实现：`src/structured_llm/contract/`  

输出形态：**`<think>` → `[json]…[/json]`**（已移除 `<state>` / `<abstract>`）。

---

## 硬失败（任一即拒收）

| 编号 | 规则 | 说明 |
|------|------|------|
| H1 | 块顺序与标签 | 必须且仅按 `<think>` → `[json]{...}[/json]` |
| H2 | JSON 可解析 | `[json]` 内必须是对象，且通过 `schemas/echo_turn.schema.json` |
| H3 | 必填字段 | `utter` / `emotion` / `volume` / `pace` / `should_speak` / `intent` / `ui_mode` / `end_turn` |
| H4 | 枚举与范围 | 各枚举合法；`volume` ∈ [0, 100] |
| H5 | TTS 安全 `utter` | 不得含结构标签；不得含括号演技注释 |
| H6 | 静音一致性 | `can_speak=false` ⇒ `should_speak=false` 且 `ui_mode=text_only` |

## 警告（不拒收，但报告）

| 编号 | 规则 |
|------|------|
| W1 | `think` 为空 |
| W2 | `utter` 过长（默认 > 80 字） |

## 覆盖面

合成集应覆盖：疲惫 / 开心 / 焦虑 / 平静 / 玩笑 / 静音 / 收束 / 打断。

## 划分与重生

```bash
# 推荐：人工撰写多样性样本（口播一一对应，非模板池抽样）
python scripts/build_echo_handcrafted.py
python scripts/validate_data.py --data examples/echo/sample_data/train.json
python scripts/validate_data.py --data examples/echo/sample_data/val.json

# 可选对照：旧版模板合成（易复读，不推荐作为主训练集）
# python scripts/generate_echo_data.py --count 300 --seed 3407
```

> 契约变更后需 **重新 SFT**；旧 LoRA（v1/v2）与 v3 不兼容。

## DPO 偏好对（可选）

`chosen` 必须满足上文硬失败规则；`rejected` 可为坏格式或合法但更差的回复。

```bash
python scripts/build_preference_data.py --sft-data examples/echo/sample_data/train.json --out-dir examples/echo/sample_data/preference --contract echo
python scripts/validate_preference_data.py --data examples/echo/sample_data/preference/train.json
```
