# structured-llm-pipeline

**Fine-tune small LLMs so structured output is reliable — not a prompt lottery.**

When you ship a **1.7B / 3B / 8B** model on-device or on a cheap GPU, you often need more than “good chat.” You need a **fixed contract**: every turn must be machine-parseable for TTS, UI state, tools, or a game engine. Prompting a frontier model can fake this in demos; **small models need the format welded in via SFT**, then proven with validators and eval suites.

This repo is a reusable pipeline for that job, with a concrete demo: **Echo** — a voice-ready character assistant.

---

## Why this exists (the core thesis)

| Approach | What you get | Where it breaks |
|----------|--------------|-----------------|
| Prompt a large API model | Flexible prose, occasional JSON | Cost, latency, privacy; format still drifts |
| Prompt a small local model | Cheap & private | **Format compliance collapses** under length, multi-turn, edge cases |
| **SFT a small model on a strict contract** | Cheap + private + **~deterministic structure** | Needs data discipline + eval (this repo) |

**Product reality:** downstream systems do not consume “vibes.” They consume fields.

```text
one generation
    ├── <think>     → optional debug / training signal
    ├── <state>     → client / session state machine
    ├── { json }    → TTS + UI + actions (schema-validated)
    └── <abstract>  → compressed memory for the next turn
```

If `utter` contains raw tags, or `volume` is missing, **TTS and the client break**. That is why “almost 100% schema-valid” is a feature, not a nicety — and why SFT + validation beats hoping the base model cooperates.

This pattern is **domain-agnostic**: voice agents, tool routers, RPG engines, IoT command+reply, form fillers — anywhere a small model must speak to both humans and machines in one shot.

---

## Demo: Echo (voice character assistant)

Echo is a fictional on-device companion. Each turn must drive **three channels at once**:

| Channel | Consumer | Contract field(s) |
|---------|----------|-------------------|
| Spoken text | TTS | `utter` (clean, no tags) |
| Prosody / affect | TTS + avatar | `emotion`, `volume`, `pace` |
| Machine control | App | `should_speak`, `end_turn`, `<state>`, `<abstract>` |

See [`docs/schema.md`](docs/schema.md) and [`schemas/echo_turn.schema.json`](schemas/echo_turn.schema.json).

---

## Pipeline overview

```text
sample / synthetic data
        │
        ▼
  validate (format + JSON Schema)     ← catch bad labels early
        │
        ▼
  SFT (LoRA / QLoRA, e.g. Unsloth)    ← weld the contract into the weights
        │
        ▼
  eval suite                          ← format · schema · multi-turn abstract
        │
        ▼
  serve (optional FastAPI)            ← return parsed VoiceTurn, not raw text
```

---

## Quickstart

See [`docs/env.md`](docs/env.md) for venv/conda and CUDA notes.

```bash
pip install -r requirements.txt

# Validate sample data against the Echo contract
python scripts/validate_data.py --data examples/echo/sample_data/train_sample.json

# Run contract checks on model outputs (offline / fixture mode)
python scripts/evaluate.py --cases examples/echo/eval_cases.json --mode fixture

# Train (needs GPU + base model; see docs/train.md)
python scripts/train.py --config examples/echo/configs/sft_lora.yaml
```

---

## Repository layout

```text
structured-llm-pipeline/
├── README.md
├── requirements.txt
├── environment.yml
├── docs/
│   ├── schema.md              # human-readable output contract
│   ├── design.md              # why multi-block + abstract memory
│   ├── env.md                 # install / CUDA notes
│   └── train.md               # SFT notes for small models
├── schemas/
│   └── echo_turn.schema.json  # JSON Schema for the JSON block
├── src/structured_llm/
│   ├── contract/              # parse + validate multi-block turns
│   ├── data/                  # dataset helpers
│   ├── train/                 # SFT entry (Unsloth/PEFT-oriented)
│   ├── eval/                  # format / schema / multi-turn metrics
│   └── serve/                 # optional API returning parsed objects
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

## What “good” looks like (metrics to report)

For a portfolio or internal report, compare **base small model + prompt** vs **SFT adapter** on the same eval set:

- **Format valid rate** — correct block order & tags (`think` → `state` → JSON → `abstract`)
- **Schema valid rate** — JSON parses and passes JSON Schema (required fields, ranges)
- **TTS-safe `utter` rate** — no nested tags / stage directions that would be spoken aloud
- **Multi-turn abstract usefulness** — next turn still coherent when only abstracts are kept

The headline claim you want to support empirically:

> On a 1.7B–8B model, SFT lifts structured compliance from “prompt lottery” to **near-contract-perfect**, at a fraction of large-API cost.

(Plug in your real numbers after you run eval.)

---

## Design principles

1. **Contract first** — schema and validators exist before training.
2. **Train/serve parity** — the same parser runs on labels and on generations.
3. **Small model by default** — optimize for local / edge deployment assumptions.
4. **Demo ≠ framework** — Echo shows the pattern; swap the schema for your domain.

---

## License

MIT (or your choice). Demo persona and sample dialogues are fictional; do not include proprietary datasets.
