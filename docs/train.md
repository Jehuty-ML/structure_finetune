# 训练说明

## 目标

让 **小基座模型**（如 Qwen2.5 / Qwen3 的 1.7B～8B）稳定输出通过契约的 Echo 回合。

## 环境

```bash
pip install -r requirements.txt
```

venv/conda 与 CUDA torch 细节见 [`env.md`](env.md)。

## 推荐配置

- **方法：** Unsloth 或 PEFT + TRL `SFTTrainer` 做 LoRA / QLoRA（4-bit）
- **目标：** 完整 assistant 消息 = 多块字符串（见 `docs/schema.md`）
- **Packing：** 对较长结构化回合默认关闭，除非已验证 EOS / 边界行为
- **训练中评测：** token 准确率可选；**训后契约评测**才是真正门槛

## 配置

见 `examples/echo/configs/sft_lora.yaml`。将 `model_name_or_path` 指向本地或 Hub 基座模型。

```bash
python scripts/train.py --config examples/echo/configs/sft_lora.yaml
```

`src/structured_llm/train/` 默认以 `dry_run` 模式启动（仅做契约检查）。真实训练需在此接入 Unsloth/PEFT。标签必须先通过 `scripts/validate_data.py`。

## 训练之后

```bash
python scripts/evaluate.py \
  --cases examples/echo/eval_cases.json \
  --mode generate \
  --base-model /path/to/base \
  --adapter /path/to/lora
```

与不带 `--adapter` 的 `--mode generate`（纯 Prompt 基线）对比，量化「焊进契约」带来的提升。
