# Echo 输出契约（v3）

每一轮助手回复 **必须** 按以下块顺序，块与块之间空一行：

1. `<think>...</think>` — 仅训练/调试用，**服务端可剥离，不下发 TTS**
2. `[json]{...}[/json]` — **唯一机器可读契约**（口播 + 客户端控制），内容过 JSON Schema

> 已废弃：自由文本 `<state>`、自由文本 `<abstract>`。多轮记忆由客户端保留对话历史（或 Prior 行），不再让模型另写一块不可校验文本。

## JSON 对象

由 [`schemas/echo_turn.schema.json`](../schemas/echo_turn.schema.json) 校验。定界标签为 `[json]…[/json]`，便于与 `<think>` 块对齐解析。

### 口播通道（给人听）

| 字段 | 类型 | 规则 |
|------|------|------|
| `utter` | string | 仅口播文本。禁止 XML/标签，禁止 `(演技注释)`。长度 ≥ 1。 |
| `emotion` | 枚举 | `gentle` \| `cheerful` \| `calm` \| `concerned` \| `playful` \| `neutral` |
| `volume` | int | 0–100 |
| `pace` | 枚举 | `slow` \| `normal` \| `fast` |
| `should_speak` | bool | 本轮是否 TTS 播放 |

### 控制通道（给 App / 状态机）

| 字段 | 类型 | 规则 |
|------|------|------|
| `intent` | 枚举 | 本轮对客户端的意图标签，供 UI/路由切换 |
| `ui_mode` | 枚举 | `speak` \| `text_only` \| `listen` |
| `end_turn` | bool | 是否让出话轮 / 结束本段交互 |

`intent` 取值：

- `comfort` — 安抚陪伴
- `celebrate` — 祝贺打气
- `clarify` — 澄清追问
- `chat` — 普通闲聊
- `joke` — 轻松玩笑
- `close` — 收束结束
- `interrupt_ack` — 确认打断并缩短

## 为什么这样拆

| 块 | 消费者 | 不这样做会怎样 |
|----|--------|----------------|
| `think` | 训练/日志 | 若塞进 `utter`，TTS 会读出推理 |
| `[json]` | TTS + App | 缺字段则播报或状态机失败；裸 JSON 边界更难切 |

## 硬失败 / 警告

完整清单见 [`data_quality.md`](data_quality.md)。要点：

- 块顺序固定；`[json]` 内必须过 Schema
- `device.can_speak=false` ⇒ `should_speak=false` 且 `ui_mode=text_only`
- `utter` TTS 安全

## 示例

```text
<think>
用户疲惫；短句、低音量；意图为安抚。
</think>

[json]
{"utter":"先歇一会儿，我就在这儿。","emotion":"gentle","volume":35,"pace":"slow","should_speak":true,"intent":"comfort","ui_mode":"speak","end_turn":false}
[/json]
```
