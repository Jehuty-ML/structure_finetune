# 训练说明

## 目标

让 **小基座模型**（默认 **Qwen3-1.7B**，可换 4B/8B）稳定输出通过契约的回合：

- **Echo**：`<think>` + `[json]…[/json]`
- **Quest**：`think → state → say → cmd → stats → abstract`

## 环境

```bash
pip install -r requirements.txt
# 默认 ModelScope（不走 HuggingFace）
python scripts/download_model.py --model Qwen/Qwen3-1.7B
```

详见 [`env.md`](env.md)。Windows + Torch nightly 下训练入口会 mock `torch.compile`，避免 Inductor「duplicate template name」。

## 数据门禁（必须先过）

**Echo**

```bash
python scripts/generate_echo_data.py --count 300 --seed 3407
python scripts/validate_data.py --data examples/echo/sample_data/train.json
```

**Quest**

```bash
python scripts/generate_quest_data.py --count 200 --seed 3407
python scripts/validate_data.py --contract quest --data examples/quest/sample_data/train.json
```

质量规则见 [`data_quality.md`](data_quality.md) / [`quest_schema.md`](quest_schema.md)。**校验失败不会进入 GPU 训练。**

配置里用 `contract: echo|quest` 选择门禁校验器。

## 推荐配置

- **方法：** Unsloth + TRL `SFTTrainer`（LoRA / QLoRA 4-bit）
- **目标：** ChatML 下完整 assistant = 多块契约字符串
- **Packing：** 默认关闭
- **产出：** LoRA adapter + `run_config.json`（目录名含模型/r/lr/时间戳）
- **验证集：** 默认 `eval_strategy: epoch`；训完还会再跑一次 `evaluate()`

## 跑训练

### Echo

编辑 `examples/echo/configs/sft_lora.yaml`，将 `dry_run` 设为 `false`：

```bash
python scripts/train.py --config examples/echo/configs/sft_lora.yaml
```

### Quest

编辑 `examples/quest/configs/sft_lora.yaml`（已含 `contract: quest`）：

```bash
python scripts/train.py --config examples/quest/configs/sft_lora.yaml
```

`dry_run: true` 时只跑契约门禁，便于无 GPU / CI。

切换规模示例：

```yaml
model_source: modelscope
model_name_or_path: "Qwen/Qwen3-1.7B"
# model_name_or_path: "Qwen/Qwen3-4B"
# model_name_or_path: "Qwen/Qwen3-8B"
```

## 训练之后

```bash
# Echo
python scripts/evaluate.py --mode generate --adapter outputs/echo_lora/<run> --compare
python scripts/chat_echo.py --adapter outputs/echo_lora/<run> --accept

# Quest
python scripts/evaluate.py --contract quest --mode generate --adapter outputs/quest_lora/<run> --compare
python scripts/chat_quest.py --adapter outputs/quest_lora/<run> --accept
```
