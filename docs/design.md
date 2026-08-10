# Design notes

## Problem

Small LLMs are attractive for voice companions (latency, cost, privacy), but product surfaces need **structured side channels** in the same generation as natural language. Prompt-only control is unstable on 1.7B–8B models once you add multi-turn history, long system prompts, or edge-case user text.

## Solution shape

1. **Freeze a contract** (tags + JSON Schema) shared by data labeling, training targets, eval, and serving.
2. **SFT** so the model emits the contract by default (LoRA/QLoRA is enough for format + style).
3. **Validate everything** — reject bad training rows; score generations with the same parser.
4. **Compress memory** with `<abstract>` so multi-turn context stays short without losing continuity.

## Why multi-block instead of “JSON only”?

- TTS and debug/training signals should not live inside the spoken string.
- `<think>` / `<state>` can be stripped before playback while still supervising the model.
- `<abstract>` is a deliberate, model-authored summary — better than truncating raw history.

## Portability

Replace Echo’s JSON Schema and system prompt to reuse the same pipeline for tool-calling agents, game masters, or IoT “say + act” controllers. The invariant is: **small model + fixed contract + SFT + shared validator**.
