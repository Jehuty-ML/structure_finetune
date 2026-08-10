# Echo 输出契约

每一轮助手回复 **必须** 按以下块顺序，块与块之间空一行：

1. `<think>...</think>`
2. `<state>...</state>`
3. 一个 JSON 对象
4. `<abstract>...</abstract>`

## JSON 对象（机器 + TTS 通道）

由 [`schemas/echo_turn.schema.json`](../schemas/echo_turn.schema.json) 校验。

| 字段 | 类型 | 规则 |
|------|------|------|
| `utter` | string | 仅口播文本。禁止 XML/标签，禁止 `(演技注释)`。长度 ≥ 1。 |
| `emotion` | 字符串枚举 | 如 `gentle`、`cheerful`、`calm`、`concerned`、`playful` |
| `volume` | int | 0–100 |
| `pace` | 字符串枚举 | `slow` \| `normal` \| `fast` |
| `should_speak` | bool | 本轮是否应 TTS 播放 |
| `end_turn` | bool | 提示助手让出话轮 |

## 软规则（校验器中作警告或硬失败）

- 每类标签恰好一对；`abstract` 内禁止嵌套结构标签。
- `abstract` 是给 *下一轮* 用户输入用的记忆——短、事实性、无角色扮演标签。
- `<state>` 在 Demo 客户端中可自由文本；训练数据里保持短且确定。

## 示例

```text
<think>
用户听起来很累；utter 宜短，音量宜低。
</think>

<state>
tone=soft; energy_hint=low
</state>

{"utter":"先歇一会儿，我就在这儿。","emotion":"gentle","volume":35,"pace":"slow","should_speak":true,"end_turn":false}

<abstract>
用户表示疲惫；以短句轻声安抚。
</abstract>
```
