# 训练说明

## 目标

让 **小基座模型**（默认 **Qwen3-1.7B**，可换 4B/8B；Qwen3.5 起体积更大）稳定输出通过契约的 Echo 回合。

## 环境

```bash
pip install -r requirements.txt
# 默认 ModelScope（不走 HuggingFace）
python scripts/download_model.py --model Qwen/Qwen3-1.7B
```

详见 [`env.md`](env.md)。Windows + Torch nightly 下训练入口会 mock `torch.compile`，避免 Inductor「duplicate template name」。

## 数据门禁（必须先过）

```bash
python scripts/generate_echo_data.py --count 300 --seed 3407
python scripts/validate_data.py --data examples/echo/sample_data/train.json
python scripts/validate_data.py --data examples/echo/sample_data/val.json
```

质量规则见 [`data_quality.md`](data_quality.md)。**校验失败不会进入 GPU 训练。**

## 推荐配置

- **方法：** Unsloth + TRL `SFTTrainer`（LoRA / QLoRA 4-bit）
- **目标：** ChatML 下完整 assistant = 多块契约字符串
- **Packing：** 默认关闭
- **产出：** LoRA adapter + `run_config.json`（目录名含模型/r/lr/时间戳）
- **验证集：** 默认 `eval_strategy: epoch`；训完还会再跑一次 `evaluate()`（短训不会因为 `eval_steps` 太大而跳过）

## 跑训练

编辑 `examples/echo/configs/sft_lora.yaml`：

1. 确认 `model_source: modelscope` 与 `model_name_or_path`
2. 确认 `data_path` / `val_data_path` 指向已校验数据
3. 将 `dry_run` 设为 `false`

```bash
python scripts/train.py --config examples/echo/configs/sft_lora.yaml
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

接入阶段 3 的 `evaluate --mode generate`，对比 base vs adapter 的格式合法率。
