# Echo output contract

Every assistant turn MUST follow this exact block order, separated by blank lines:

1. `<think>...</think>`
2. `<state>...</state>`
3. a single JSON object
4. `<abstract>...</abstract>`

## JSON object (machine + TTS channel)

Validated by [`schemas/echo_turn.schema.json`](../schemas/echo_turn.schema.json).

| Field | Type | Rules |
|-------|------|--------|
| `utter` | string | Spoken text only. No XML/tags, no `(stage directions)`. Length ≥ 1. |
| `emotion` | string enum | e.g. `gentle`, `cheerful`, `calm`, `concerned`, `playful` |
| `volume` | int | 0–100 |
| `pace` | string enum | `slow` \| `normal` \| `fast` |
| `should_speak` | bool | Whether TTS should play this turn |
| `end_turn` | bool | Hint that the assistant is yielding the floor |

## Soft rules (enforced in validators as warnings or hard fails)

- Exactly one pair of each tag; no nesting inside `abstract`.
- `abstract` is memory for the *next* user turn — short, factual, no roleplay tags.
- `<state>` is free-form for the demo client; keep it short and deterministic in training data.

## Example

```text
<think>
User sounds tired; keep utter short and lower volume.
</think>

<state>
tone=soft; energy_hint=low
</state>

{"utter":"Rest a bit — I'm right here.","emotion":"gentle","volume":35,"pace":"slow","should_speak":true,"end_turn":false}

<abstract>
User felt tired; replied with a short soft reassurance.
</abstract>
```
