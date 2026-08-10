# Training notes

## Goal

Teach a **small base model** (e.g. Qwen2.5 / Qwen3 1.7B–8B) to emit Echo turns that pass the contract at high rate.

## Environment

```bash
pip install -r requirements.txt
```

See [`env.md`](env.md) for venv/conda details and CUDA torch notes.

## Recommended setup

- **Method:** LoRA or QLoRA (4-bit) via Unsloth or PEFT + TRL `SFTTrainer`
- **Target:** full assistant message = multi-block string (see `docs/schema.md`)
- **Packing:** off for long structured turns unless you verify EOS / boundary behavior
- **Eval during train:** token accuracy is optional; **post-hoc contract eval** is the real gate

## Config

See `examples/echo/configs/sft_lora.yaml`. Point `model_name_or_path` at a local or Hub base model.

```bash
python scripts/train.py --config examples/echo/configs/sft_lora.yaml
```

`src/structured_llm/train/` starts in `dry_run` mode (contract-check only). Wire Unsloth/PEFT there for a real run. Labels must already pass `scripts/validate_data.py`.

## After training

```bash
python scripts/evaluate.py \
  --cases examples/echo/eval_cases.json \
  --mode generate \
  --base-model /path/to/base \
  --adapter /path/to/lora
```

Compare against `--mode generate` without `--adapter` (prompt-only baseline) to quantify the “welded contract” lift.
