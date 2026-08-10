# structured-llm-pipeline

**把小模型的结构化输出训稳——而不是靠 Prompt 碰运气。**

当你要在端侧或低成本 GPU 上部署 **1.7B / 3B / 8B** 模型时，往往不只是「会聊天」。你需要一份 **固定契约**：每一轮输出都能被 TTS、UI 状态机、工具或游戏引擎稳定解析。大模型 API + Prompt 可以在演示里凑合；**小模型要把格式通过 SFT 焊进权重**，再用校验与评测证明它靠谱。

本仓库是一套可复用流水线，Demo 场景为 **Echo**：面向语音播报的角色助手。

---

## 为什么做这个（核心论点）

| 做法 | 你得到什么 | 哪里会崩 |
|------|------------|----------|
| Prompt 调大模型 API | 文案灵活，偶尔能出 JSON | 成本、延迟、隐私；格式仍会漂移 |
| Prompt 调本地小模型 | 便宜、可私有化 | **一加长上下文 / 多轮 / 边角输入，格式合规率就垮** |
| **按严格契约对小模型做 SFT** | 便宜 + 私有 + **结构近似确定** | 需要数据纪律与评测（本仓库） |

**产品现实：** 下游系统不消费「感觉」，只消费字段。

```text
一次生成
    ├── <think>     → 可选：调试 / 训练信号
    ├── <state>     → 客户端 / 会话状态机
    ├── { json }    → TTS + UI + 动作（Schema 校验）
    └── <abstract>  → 压缩记忆，供下一轮使用
```

若 `utter` 里夹了标签，或缺少 `volume`，**TTS 与客户端会直接坏掉**。所以「接近 100% Schema 合法」是功能要求，不是锦上添花——SFT + 校验远胜于指望基座模型自觉配合。

该模式与具体业务无关：语音助手、工具路由、RPG 引擎、IoT「边说边控」、表单填充——凡是小模型要在一次生成里同时服务人和机器，都可以用。

---

## Demo：Echo（语音角色助手）

Echo 是虚构的端侧伙伴。每一轮必须同时驱动 **三条通道**：

| 通道 | 消费者 | 契约字段 |
|------|--------|----------|
| 口播文本 | TTS | `utter`（干净、无标签） |
| 韵律 / 情绪 | TTS + 形象 | `emotion`、`volume`、`pace` |
| 机器控制 | App | `should_speak`、`end_turn`、`<state>`、`<abstract>` |

详见 [`docs/schema.md`](docs/schema.md) 与 [`schemas/echo_turn.schema.json`](schemas/echo_turn.schema.json)。

项目计划 / 里程碑：[`docs/roadmap.md`](docs/roadmap.md)。

---

## 流水线概览

```text
样例 / 合成数据
        │
        ▼
  校验（格式 + JSON Schema）      ← 尽早拦住坏标签
        │
        ▼
  SFT（LoRA / QLoRA，如 Unsloth） ← 把契约焊进权重
        │
        ▼
  评测套件                        ← 格式 · Schema · 多轮 abstract
        │
        ▼
  服务（可选 FastAPI）            ← 返回解析后的 VoiceTurn，而非裸文本
```

---

## 快速开始

环境与 CUDA 说明见 [`docs/env.md`](docs/env.md)。

```bash
pip install -r requirements.txt

# 按 Echo 契约校验样例数据
python scripts/validate_data.py --data examples/echo/sample_data/train_sample.json

# 对模型输出做契约检查（离线 / fixture 模式）
python scripts/evaluate.py --cases examples/echo/eval_cases.json --mode fixture

# 训练（需要 GPU + 基座模型；见 docs/train.md）
python scripts/train.py --config examples/echo/configs/sft_lora.yaml
```

---

## 仓库结构

```text
structured-llm-pipeline/
├── README.md
├── requirements.txt
├── environment.yml
├── docs/
│   ├── schema.md              # 可读的输出契约说明
│   ├── design.md              # 为何多块输出 + abstract 记忆
│   ├── env.md                 # 安装 / CUDA 说明
│   ├── train.md               # 小模型 SFT 说明
│   └── roadmap.md             # 项目计划与里程碑
├── schemas/
│   └── echo_turn.schema.json  # JSON 块的 JSON Schema
├── src/structured_llm/
│   ├── contract/              # 多块回合的解析与校验
│   ├── data/                  # 数据集辅助
│   ├── train/                 # SFT 入口（面向 Unsloth/PEFT）
│   ├── eval/                  # 格式 / Schema / 多轮指标
│   └── serve/                 # 可选：返回解析对象的 API 辅助
├── examples/echo/
│   ├── prompts/
│   ├── sample_data/
│   ├── eval_cases.json
│   └── configs/
└── scripts/
    ├── validate_data.py
    ├── train.py
    ├── evaluate.py
    └── serve.py
```

---

## 什么叫「做好了」（建议汇报的指标）

作品集或内部报告中，在同一评测集上对比 **小模型 + 纯 Prompt** vs **SFT adapter**：

- **格式合法率** — 块顺序与标签正确（`think` → `state` → JSON → `abstract`）
- **Schema 合法率** — JSON 可解析且通过 Schema（必填字段、取值范围）
- **TTS 安全 `utter` 率** — 无嵌套标签、无会被朗读出来的括号演技注释
- **多轮 abstract 可用性** — 只保留 abstract 时下一轮仍连贯

你要用实验支撑的标题结论：

> 在 1.7B～8B 模型上，SFT 把结构化合规从「Prompt 抽奖」提升到 **接近契约满分**，成本远低于大模型 API。

（跑完评测后填入真实数字。）

---

## 设计原则

1. **契约优先** — 先有 Schema 与校验器，再训练。
2. **训推一致** — 标签与生成共用同一套解析器。
3. **默认小模型** — 按本地 / 端侧部署假设优化。
4. **Demo ≠ 框架** — Echo 只示范模式；换 Schema 即可迁到你的领域。

---

## 许可证

MIT（或自选）。Demo 人设与样例对话均为虚构；请勿纳入专有数据集。
