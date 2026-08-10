# structured-llm-pipeline

**把小模型的结构化输出训稳——而不是靠 Prompt 碰运气。**

> **English:** A reproducible pipeline to **SFT small LLMs (1.7B–8B) into a fixed output contract** (parseable by TTS / UI / tools)—not prompt lottery. Demo: **Echo**, a fictional on-device voice companion. Contract v3: `<think>` + `[json]{…}[/json]`. Validate → train (optional GPU) → eval → FastAPI returning structured `VoiceTurn`.

当你要在端侧或低成本 GPU 上部署 **1.7B / 3B / 8B** 模型时，往往不只是「会聊天」。你需要一份 **固定契约**：每一轮输出都能被 TTS、UI 状态机、工具或游戏引擎稳定解析。大模型 API + Prompt 可以在演示里凑合；**小模型要把格式通过 SFT 焊进权重**，再用校验与评测证明它靠谱。

本仓库是一套可复用流水线，Demo 场景为 **Echo**：面向语音播报的角色助手。许可证：[MIT](LICENSE)。

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
    ├── <think>          → 可选：调试 / 训练信号（可剥离）
    └── [json]{…}[/json] → TTS + App 控制（Schema 校验：口播 + intent/ui_mode）
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
| 机器控制 | App | `intent`、`ui_mode`、`should_speak`、`end_turn` |

详见 [`docs/schema.md`](docs/schema.md) 与 [`schemas/echo_turn.schema.json`](schemas/echo_turn.schema.json)。

### 输出格式示例

每一轮助手回复固定两块（块间空一行）：

```text
<think>
用户疲惫；短句、低音量；意图安抚。
</think>

[json]
{"utter":"没事，我在这儿。你先歇着。","emotion":"gentle","volume":30,"pace":"slow","should_speak":true,"intent":"comfort","ui_mode":"speak","end_turn":false}
[/json]
```

| 块 | 给谁用 | 说明 |
|----|--------|------|
| `<think>` | 训练 / 日志 | 可剥离，**不下发 TTS** |
| `[json]…[/json]` | TTS + App | **唯一机器契约**，内层对象必须过 Schema |

### JSON 字段含义与使用情景

**口播 / TTS**

| 字段 | 含义 | 使用情景 |
|------|------|----------|
| `utter` | 要念/显示的话 | 送给 TTS；静音时也可当屏幕字幕 |
| `emotion` | 情绪风格 | 驱动音色/表情（`gentle` / `cheerful` / `calm` / `concerned` / `playful` / `neutral`） |
| `volume` | 音量 0–100 | 疲惫→低，庆祝→高，静音→0 |
| `pace` | 语速 | 安抚 `slow`，打断确认 `fast`，一般 `normal` |
| `should_speak` | 本轮是否出声 | `false` 时 TTS 不播（图书馆、开会） |

**App / 状态机**

| 字段 | 含义 | 使用情景 |
|------|------|----------|
| `intent` | 本轮意图标签 | UI 路由：安抚、祝贺、追问、闲聊、玩笑、收束、确认打断 |
| `ui_mode` | 界面模式 | `speak` 播报 / `text_only` 只出字 / `listen` 聆听态 |
| `end_turn` | 是否结束本段 | `true` 时停麦、关会话（用户说「先这样」） |

`intent` 枚举：`comfort` · `celebrate` · `clarify` · `chat` · `joke` · `close` · `interrupt_ack`。

硬约束一例：`device.can_speak=false` ⇒ `should_speak=false` 且 `ui_mode=text_only`。

### 解析示例

训练数据、评测、服务共用同一套解析器：

```python
from structured_llm.contract import validate_turn

raw = """<think>
用户疲惫；短句、低音量；意图安抚。
</think>

[json]
{"utter":"没事，我在这儿。你先歇着。","emotion":"gentle","volume":30,"pace":"slow","should_speak":true,"intent":"comfort","ui_mode":"speak","end_turn":false}
[/json]"""

result = validate_turn(raw, schema_path="schemas/echo_turn.schema.json")
if result.ok:
    p = result.parsed
    print(p.think)             # 调试文本
    print(p.payload["utter"])  # → TTS
    print(p.payload["intent"]) # → App 路由
else:
    print(result.errors)       # 格式/Schema 错误列表
```

批量校验样例数据：

```bash
python scripts/validate_data.py --data examples/echo/sample_data/train.json
```

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
  评测套件                        ← 格式 · Schema · TTS 安全 · 多轮承接
        │
        ▼
  真机对话 / 可选 API           ← chat_echo：生成+解析；HTTP 仅附录测解析
```

---

## 快速开始

### 最小路径（无 GPU）

环境与 CUDA 说明见 [`docs/env.md`](docs/env.md)。轻量依赖见 `requirements-min.txt`。

```bash
pip install -r requirements-min.txt
# 已有 llm_dev 等训练环境也请执行上一行（补齐 fastapi/uvicorn）

# 合成并划分 train/val（或直接使用已提交的数据）
python scripts/generate_echo_data.py --count 300 --seed 3407

# 按 Echo 契约校验
python scripts/validate_data.py --data examples/echo/sample_data/train.json
python scripts/validate_data.py --data examples/echo/sample_data/val.json

# 对模型输出做契约检查（离线 / fixture 模式）
python scripts/evaluate.py --cases examples/echo/eval_cases.json --mode fixture

# 可选：契约门禁 dry-run（不占 GPU）
# 将 examples/echo/configs/sft_lora.yaml 中 dry_run 设为 true 后：
# python scripts/train.py --config examples/echo/configs/sft_lora.yaml
```

### 训练与对比评测（需 GPU）

完整依赖见 `requirements.txt`（建议 conda 环境）。详见 [`docs/train.md`](docs/train.md)。

```bash
# 训练（先契约门禁；基座默认 ModelScope）
python scripts/train.py --config examples/echo/configs/sft_lora.yaml

# 真机对比：Prompt-only 基座 vs LoRA
python scripts/evaluate.py --mode generate --compare `
  --base-model Qwen/Qwen3-1.7B `
  --adapter outputs/echo_lora/Qwen3-1.7B_r16_len2048_lr2e-4_0811_1043 `
  --json-out outputs/eval_compare_v3.json
```

### 服务 / 真机对话演示

详见 [`docs/serve.md`](docs/serve.md)、[`docs/roadmap.md`](docs/roadmap.md) 阶段 4。

**主路径（需 GPU + LoRA）：**

```bash
# 固定场景验收
python scripts/chat_echo.py `
  --adapter outputs/echo_lora/Qwen3-1.7B_r16_len2048_lr2e-4_0811_1043 `
  --accept

# 交互真聊
python scripts/chat_echo.py `
  --adapter outputs/echo_lora/Qwen3-1.7B_r16_len2048_lr2e-4_0811_1043
```

**附录（无 GPU，只测解析器）：**

```bash
python scripts/serve_api.py --host 127.0.0.1 --port 8000
python scripts/smoke_serve.py
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
│   ├── design.md              # 为何 think + [json] 契约
│   ├── env.md                 # 安装 / CUDA 说明
│   ├── train.md               # 小模型 SFT 说明
│   ├── data_quality.md        # 硬失败 / 警告规则
│   ├── results.md             # 评测对比数字
│   ├── serve.md               # 阶段4：真聊为主，HTTP 解析为辅
│   └── roadmap.md             # 项目计划
├── schemas/
│   └── echo_turn.schema.json  # [json] 内对象的 JSON Schema
├── src/structured_llm/
│   ├── contract/              # 多块回合的解析与校验
│   ├── data/                  # 数据集辅助
│   ├── train/                 # SFT 入口（面向 Unsloth/PEFT）
│   ├── eval/                  # 格式 / Schema / TTS / 多轮指标
│   └── serve/                 # FastAPI：返回解析后的 VoiceTurn
├── examples/echo/
│   ├── prompts/
│   ├── sample_data/
│   ├── eval_cases.json
│   └── configs/
├── LICENSE
├── requirements-min.txt       # 无 GPU 最小依赖
└── scripts/
    ├── validate_data.py
    ├── train.py
    ├── evaluate.py
    ├── chat_echo.py           # 真机对话（LoRA 生成 + 契约解析）
    ├── serve.py               # CLI：解析单段生成文本
    ├── serve_api.py           # 可选：FastAPI 只做解析
    ├── demo_request.py        # 可选：假 raw 打 API
    └── smoke_serve.py         # 可选：API 冒烟
```

---

## 什么叫「做好了」（建议汇报的指标）

作品集报告中，在同一评测集上对比 **小模型 + 纯 Prompt** vs **SFT adapter**：

- **格式合法率** — 块顺序与标签正确（`think` → `[json]…[/json]`）
- **Schema 合法率** — `[json]` 内可解析且通过 Schema（必填字段、取值范围）
- **TTS 安全 `utter` 率** — 无嵌套标签、无会被朗读出来的括号演技注释
- **多轮承接** — 带 Prior 上下文时仍遵守契约并承接话题

实测（契约 v3，Qwen3-1.7B，Echo 3 条评测集，详见 [`docs/results.md`](docs/results.md)）：

| 设置 | 通过率 | 格式合法率 | TTS 安全率 |
|------|--------|------------|------------|
| 基座 + Prompt | 33.3% | 33.3% | 66.7% |
| 基座 + LoRA SFT | **100%** | **100%** | **100%** |

Adapter：`outputs/echo_lora/Qwen3-1.7B_r16_len2048_lr2e-4_0811_1043`

> 小模型靠 Prompt「抽奖」焊不住契约；短 SFT 即可把格式合规从近 0 拉到可用，并稳住多轮承接。

---

## 设计原则

1. **契约优先** — 先有 Schema 与校验器，再训练。
2. **训推一致** — 标签与生成共用同一套解析器。
3. **默认小模型** — 按本地 / 端侧部署假设优化。
4. **Demo ≠ 框架** — Echo 只示范模式；换 Schema 即可迁到你的领域。

---

## 许可证

[MIT](LICENSE)。Demo 人设与样例对话均为虚构；请勿纳入非公开数据集。
