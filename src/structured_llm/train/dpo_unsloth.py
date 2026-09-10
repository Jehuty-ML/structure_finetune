"""Unsloth + TRL DPO：在契约合规基础上偏好更好的 chosen。"""

from __future__ import annotations

import inspect
import json
import os
from pathlib import Path
from typing import Any

from structured_llm.train.sft_unsloth import _resolve_output_dir, _setup_env


def _make_dpo_args(config: dict[str, Any], actual_output_dir: Path, *, bf16: bool) -> Any:
    """兼容不同 trl 版本：优先 DPOConfig，否则 TrainingArguments。"""
    common = dict(
        output_dir=str(actual_output_dir),
        per_device_train_batch_size=int(config.get("per_device_train_batch_size", 1)),
        gradient_accumulation_steps=int(config.get("gradient_accumulation_steps", 8)),
        per_device_eval_batch_size=1,
        warmup_steps=int(config.get("warmup_steps", 10)),
        num_train_epochs=float(config.get("num_train_epochs", 1)),
        learning_rate=float(config.get("learning_rate", 5e-6)),
        fp16=False,
        bf16=bf16,
        logging_steps=int(config.get("logging_steps", 5)),
        optim=str(config.get("optim", "paged_adamw_8bit")),
        weight_decay=float(config.get("weight_decay", 0.01)),
        lr_scheduler_type=str(config.get("lr_scheduler_type", "cosine")),
        seed=int(config.get("seed", 3407)),
        save_strategy="epoch",
        save_total_limit=2,
        report_to="none",
        remove_unused_columns=False,
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
    )
    beta = float(config.get("beta", 0.1))
    max_length = int(config.get("max_seq_length", 2048))
    max_prompt_length = int(config.get("max_prompt_length", max_length // 2))

    try:
        from trl import DPOConfig

        params = set(inspect.signature(DPOConfig.__init__).parameters)
        kwargs = {k: v for k, v in common.items() if k in params or k == "output_dir"}
        if "beta" in params:
            kwargs["beta"] = beta
        if "max_length" in params:
            kwargs["max_length"] = max_length
        if "max_prompt_length" in params:
            kwargs["max_prompt_length"] = max_prompt_length
        if "dataset_num_proc" in params:
            kwargs["dataset_num_proc"] = int(config.get("dataset_num_proc", 1))
        return DPOConfig(**kwargs)
    except Exception:
        from transformers import TrainingArguments

        return TrainingArguments(**common)


def _build_dpo_trainer(
    *,
    model: Any,
    tokenizer: Any,
    train_ds: Any,
    eval_ds: Any,
    args: Any,
    config: dict[str, Any],
) -> Any:
    from trl import DPOTrainer

    beta = float(config.get("beta", 0.1))
    max_length = int(config.get("max_seq_length", 2048))
    max_prompt_length = int(config.get("max_prompt_length", max_length // 2))
    sig = inspect.signature(DPOTrainer.__init__)
    params = set(sig.parameters)

    kwargs: dict[str, Any] = {
        "model": model,
        "ref_model": None,
        "args": args,
        "train_dataset": train_ds,
    }
    if eval_ds is not None and "eval_dataset" in params:
        kwargs["eval_dataset"] = eval_ds

    if "processing_class" in params:
        kwargs["processing_class"] = tokenizer
    elif "tokenizer" in params:
        kwargs["tokenizer"] = tokenizer

    # 较新 DPOConfig 已含 beta/max_*；旧版挂在 Trainer 上
    if "beta" in params and not hasattr(args, "beta"):
        kwargs["beta"] = beta
    if "max_length" in params and not hasattr(args, "max_length"):
        kwargs["max_length"] = max_length
    if "max_prompt_length" in params and not hasattr(args, "max_prompt_length"):
        kwargs["max_prompt_length"] = max_prompt_length

    return DPOTrainer(**kwargs)


def run_unsloth_dpo(config: dict[str, Any], project_root: Path) -> Path:
    """
    真实 DPO。调用前须已通过偏好门禁（chosen 契约必过）。
    保存 LoRA adapter（非 merge）。可选从 sft_adapter_path 热启动。
    """
    _setup_env(project_root)

    from structured_llm.data.preference import (
        format_dpo_prompt,
        iter_dpo_rows,
        preference_to_trl_columns,
    )
    from structured_llm.train.model_source import resolve_model_path

    model_id = config["model_name_or_path"]
    model_source = str(config.get("model_source", "modelscope"))
    want_local_only = bool(config.get("local_files_only", False))
    resolved = resolve_model_path(
        model_id,
        project_root=project_root,
        source=model_source,
        local_files_only=want_local_only,
        cache_subdir=str(config.get("model_cache_dir", "models/base")),
    )
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

    import torch
    from datasets import Dataset
    from unsloth import FastLanguageModel

    try:
        from unsloth import PatchDPOTrainer

        PatchDPOTrainer()
    except Exception as exc:  # noqa: BLE001 — 旧 Unsloth 可能无此符号
        print(f"[warn] PatchDPOTrainer 不可用，继续：{exc}")

    model_name = resolved
    data_path = Path(config["data_path"])
    val_path = config.get("val_data_path")
    system_prompt_path = config.get("system_prompt_path")
    max_seq_length = int(config.get("max_seq_length", 2048))
    load_in_4bit = bool(config.get("load_in_4bit", True))
    seed = int(config.get("seed", 3407))
    contract = str(config.get("contract", "echo")).lower()
    prior_label = "Abstract" if contract == "quest" else "Prior"

    default_out = (
        "outputs/quest_dpo" if contract == "quest" else "outputs/echo_dpo"
    )
    output_base = Path(config.get("output_dir", default_out))
    name_cfg = dict(config)
    name_cfg["model_name_or_path"] = model_id
    actual_output_dir = _resolve_output_dir(name_cfg, output_base)

    system_prompt = ""
    if system_prompt_path and Path(system_prompt_path).exists():
        system_prompt = Path(system_prompt_path).read_text(encoding="utf-8").strip()

    print(f"加载模型（本地）：{model_name}")
    dtype = (
        torch.bfloat16
        if torch.cuda.is_available() and torch.cuda.is_bf16_supported()
        else None
    )
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_name,
        max_seq_length=max_seq_length,
        dtype=dtype,
        load_in_4bit=load_in_4bit,
        local_files_only=True,
    )

    sft_adapter = config.get("sft_adapter_path")
    if sft_adapter:
        adapter_path = Path(str(sft_adapter))
        if not (adapter_path / "adapter_config.json").exists():
            raise FileNotFoundError(f"未找到 SFT LoRA：{adapter_path}")
        print(f"从 SFT adapter 热启动：{adapter_path}")
        from peft import PeftModel

        model = PeftModel.from_pretrained(
            model, str(adapter_path), is_trainable=True
        )
    else:
        model = FastLanguageModel.get_peft_model(
            model,
            r=int(config.get("lora_r", 16)),
            target_modules=[
                "q_proj",
                "k_proj",
                "v_proj",
                "o_proj",
                "gate_proj",
                "up_proj",
                "down_proj",
            ],
            lora_alpha=int(config.get("lora_alpha", 32)),
            lora_dropout=float(config.get("lora_dropout", 0.05)),
            bias="none",
            use_gradient_checkpointing="unsloth",
            random_state=seed,
            use_rslora=bool(config.get("use_rslora", False)),
            use_dora=bool(config.get("use_dora", False)),
        )

    train_rows = list(iter_dpo_rows(data_path))
    train_mapped = preference_to_trl_columns(
        train_rows, system_prompt=system_prompt, prior_label=prior_label
    )
    train_ds = Dataset.from_list(train_mapped)

    eval_ds = None
    if val_path and Path(val_path).exists():
        val_rows = list(iter_dpo_rows(val_path))
        eval_ds = Dataset.from_list(
            preference_to_trl_columns(
                val_rows, system_prompt=system_prompt, prior_label=prior_label
            )
        )

    # 自检：prompt 构造与门禁一致
    _ = format_dpo_prompt(
        train_rows[0]["input"],
        train_rows[0].get("prior_utters"),
        system_prompt=system_prompt,
        prior_label=prior_label,
    )

    bf16 = bool(torch.cuda.is_available() and torch.cuda.is_bf16_supported())
    dpo_args = _make_dpo_args(config, actual_output_dir, bf16=bf16)
    if eval_ds is not None and hasattr(dpo_args, "eval_strategy"):
        dpo_args.eval_strategy = str(config.get("eval_strategy", "epoch"))

    trainer = _build_dpo_trainer(
        model=model,
        tokenizer=tokenizer,
        train_ds=train_ds,
        eval_ds=eval_ds,
        args=dpo_args,
        config=config,
    )
    print(f"开始 DPO 训练 -> {actual_output_dir}")
    trainer.train()

    if eval_ds is not None:
        try:
            print("训练结束，跑 validation …")
            metrics = trainer.evaluate()
            print(f"eval metrics: {metrics}")
            (actual_output_dir / "eval_metrics.json").write_text(
                json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] DPO evaluate 跳过：{exc}")

    print("保存 LoRA adapter ...")
    model.save_pretrained(str(actual_output_dir))
    tokenizer.save_pretrained(str(actual_output_dir))
    meta = {
        "method": "dpo",
        "model_name_or_path": model_id,
        "resolved_model_path": model_name,
        "model_source": model_source,
        "sft_adapter_path": sft_adapter,
        "data_path": str(data_path),
        "val_data_path": val_path,
        "system_prompt_path": system_prompt_path,
        "contract": contract,
        "beta": config.get("beta", 0.1),
        "lora_r": config.get("lora_r"),
        "learning_rate": config.get("learning_rate"),
        "max_seq_length": max_seq_length,
    }
    (actual_output_dir / "run_config.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"完成：{actual_output_dir}")
    return actual_output_dir
