"""Unsloth + TRL SFT：将固定契约焊进小模型。"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def _setup_env(project_root: Path) -> None:
    """
    必须在 import unsloth 之前调用。
    规避 Windows + Torch nightly 上 torch.compile / Inductor
    「duplicate template name」一类崩溃。
    """
    cache = project_root / "cache" / "unsloth_compiled_cache"
    cache.mkdir(parents=True, exist_ok=True)
    init_py = cache / "__init__.py"
    if not init_py.exists():
        init_py.write_text("", encoding="utf-8")

    if str(cache) not in sys.path:
        sys.path.insert(0, str(cache))

    os.environ["UNSLOTH_COMPILE_LOCATION"] = str(cache)
    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.environ["UNSLOTH_USE_XFORMERS"] = "0"
    os.environ["UNSLOTH_USE_FLASH_ATTENTION"] = "0"
    os.environ["XFORMERS_FORCE_DISABLE_TRITON"] = "1"
    # 禁止 Dynamo 走 Inductor 模板注册路径
    os.environ.setdefault("TORCHDYNAMO_DISABLE", "1")
    os.environ.setdefault("TORCH_COMPILE_DISABLE", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

    if sys.platform == "win32":
        import io

        for stream in (sys.stdout, sys.stderr, sys.stdin):
            if isinstance(stream, io.TextIOWrapper):
                stream.reconfigure(encoding="utf-8", errors="ignore")

    import builtins

    import psutil
    import torch

    builtins.psutil = psutil

    def mock_compile(*args_compile, **_kwargs_compile):
        if len(args_compile) == 1 and callable(args_compile[0]):
            return args_compile[0]
        return lambda x: x

    if not getattr(torch, "_patched_compile", False):
        torch._original_compile = torch.compile
        torch.compile = mock_compile
        torch._patched_compile = True


def _resolve_output_dir(config: dict[str, Any], base: Path) -> Path:
    """outputs/<base>/<model>_r{r}_lr{lr}_{timestamp}"""
    model = str(config.get("model_name_or_path", "model"))
    short = Path(model).name.replace("/", "_")
    lr = config.get("learning_rate", 0)
    lr_str = f"{lr:.0e}".replace("e-0", "e-")
    stamp = datetime.now().strftime("%m%d_%H%M")
    folder = (
        f"{short}_r{config.get('lora_r', 16)}_"
        f"len{config.get('max_seq_length', 2048)}_"
        f"lr{lr_str}_{stamp}"
    )
    path = base / folder
    path.mkdir(parents=True, exist_ok=True)
    return path


def _user_content(
    input_obj: Any,
    prior_utters: Any = None,
    *,
    prior_label: str = "Prior",
) -> str:
    """与评测/聊天一致：可选 Prior（Echo）或 Abstract（Quest）+ User JSON。"""
    from structured_llm.data import format_user_message

    priors: list[str] | None
    if not prior_utters:
        priors = None
    elif isinstance(prior_utters, list):
        priors = [str(x) for x in prior_utters]
    else:
        priors = [str(prior_utters)]
    return format_user_message(input_obj, priors, prior_label=prior_label)


def run_unsloth_sft(config: dict[str, Any], project_root: Path) -> Path:
    """
    真实 SFT。调用前须已通过契约校验。
    保存 LoRA adapter（非 merge），便于评测对比。
    默认从 ModelScope 解析基座到本地路径，再交给 Unsloth（避免访问 huggingface.co）。
    """
    _setup_env(project_root)

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
    # 解析完成后禁止 HF 联网，防止 Unsloth 再去拉 unsloth/* 量化包
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

    # Unsloth 必须先于 transformers / trl / peft 导入
    import torch
    from unsloth import FastLanguageModel
    from datasets import load_dataset
    from transformers import TrainingArguments
    from trl import SFTTrainer

    model_name = resolved
    data_path = Path(config["data_path"])
    val_path = config.get("val_data_path")
    system_prompt_path = config.get("system_prompt_path")
    max_seq_length = int(config.get("max_seq_length", 2048))
    load_in_4bit = bool(config.get("load_in_4bit", True))
    seed = int(config.get("seed", 3407))

    output_base = Path(config.get("output_dir", "outputs/echo_lora"))
    # 目录名仍用原始 ID，便于辨认
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

    data_files: dict[str, str] = {"train": str(data_path)}
    if val_path and Path(val_path).exists():
        data_files["validation"] = str(val_path)
    raw = load_dataset("json", data_files=data_files)

    # 自己单进程 tokenize，避免 Unsloth 内部 num_proc=20 在 Windows 崩溃
    response_prefix = [151644, 77091]  # <|im_start|>assistant（Qwen ChatML）

    contract = str(config.get("contract", "echo")).lower()
    prior_label = "Abstract" if contract == "quest" else "Prior"

    def preprocess_and_mask(examples: dict[str, Any]) -> dict[str, Any]:
        texts: list[str] = []
        n = len(examples["input"])
        priors = examples.get("prior_utters")
        if priors is None:
            priors = [None] * n
        for input_obj, output_text, prior in zip(
            examples["input"], examples["output"], priors
        ):
            user = _user_content(input_obj, prior, prior_label=prior_label)
            text = (
                f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
                f"<|im_start|>user\n{user}<|im_end|>\n"
                f"<|im_start|>assistant\n{output_text}<|im_end|>"
            )
            if tokenizer.eos_token and not text.endswith(tokenizer.eos_token):
                text += tokenizer.eos_token
            texts.append(text)

        model_inputs = tokenizer(
            texts, max_length=max_seq_length, truncation=True, padding=False
        )
        labels: list[list[int]] = []
        for input_ids in model_inputs["input_ids"]:
            start_idx = -1
            for i in range(len(input_ids) - len(response_prefix) + 1):
                if input_ids[i : i + len(response_prefix)] == response_prefix:
                    start_idx = i + len(response_prefix)
                    if start_idx < len(input_ids) and input_ids[start_idx] == 198:
                        start_idx += 1
                    break
            if start_idx == -1:
                labels.append([-100] * len(input_ids))
            else:
                labels.append([-100] * start_idx + list(input_ids[start_idx:]))
        model_inputs["labels"] = labels
        return model_inputs

    print("单进程 tokenize 数据集 ...")
    train_ds = raw["train"].map(
        preprocess_and_mask,
        batched=True,
        num_proc=1,
        remove_columns=raw["train"].column_names,
    )
    eval_ds = None
    if "validation" in raw:
        eval_ds = raw["validation"].map(
            preprocess_and_mask,
            batched=True,
            num_proc=1,
            remove_columns=raw["validation"].column_names,
        )

    # 短训（如 1 epoch / 几十 step）时 steps 评估容易一次都不触发；
    # 默认按 epoch；也可用配置覆盖。结束后若有 val 再强制 evaluate 一次。
    eval_strategy = str(config.get("eval_strategy", "epoch" if eval_ds is not None else "no"))
    eval_steps = config.get("eval_steps")
    if eval_steps is None and eval_strategy == "steps":
        eval_steps = max(5, int(config.get("logging_steps", 5)) * 2)
    else:
        eval_steps = int(eval_steps) if eval_steps is not None else None

    training_args = TrainingArguments(
        output_dir=str(actual_output_dir),
        per_device_train_batch_size=int(config.get("per_device_train_batch_size", 1)),
        gradient_accumulation_steps=int(config.get("gradient_accumulation_steps", 8)),
        per_device_eval_batch_size=1,
        warmup_steps=int(config.get("warmup_steps", 20)),
        num_train_epochs=float(config.get("num_train_epochs", 3)),
        learning_rate=float(config.get("learning_rate", 2e-4)),
        fp16=False,
        bf16=bool(torch.cuda.is_available() and torch.cuda.is_bf16_supported()),
        logging_steps=int(config.get("logging_steps", 5)),
        optim="paged_adamw_8bit",
        weight_decay=0.01,
        lr_scheduler_type="cosine",
        seed=seed,
        eval_strategy=eval_strategy if eval_ds is not None else "no",
        eval_steps=eval_steps if eval_ds is not None and eval_strategy == "steps" else None,
        save_strategy="epoch" if eval_strategy == "epoch" else "steps",
        save_steps=int(eval_steps or 50),
        save_total_limit=2,
        report_to="none",
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
    )

    trainer_kwargs: dict[str, Any] = dict(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_ds,
        max_seq_length=max_seq_length,
        packing=bool(config.get("packing", False)),
        dataset_num_proc=1,
        args=training_args,
    )
    if eval_ds is not None:
        trainer_kwargs["eval_dataset"] = eval_ds

    trainer = SFTTrainer(**trainer_kwargs)
    print(f"开始训练 -> {actual_output_dir}")
    trainer.train()

    if eval_ds is not None:
        print("训练结束，跑 validation …")
        metrics = trainer.evaluate()
        print(f"eval metrics: {metrics}")
        (actual_output_dir / "eval_metrics.json").write_text(
            json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    print("保存 LoRA adapter ...")
    model.save_pretrained(str(actual_output_dir))
    tokenizer.save_pretrained(str(actual_output_dir))
    meta = {
        "model_name_or_path": model_id,
        "resolved_model_path": model_name,
        "model_source": model_source,
        "data_path": str(data_path),
        "val_data_path": val_path,
        "system_prompt_path": system_prompt_path,
        "lora_r": config.get("lora_r"),
        "learning_rate": config.get("learning_rate"),
        "max_seq_length": max_seq_length,
    }
    (actual_output_dir / "run_config.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"完成：{actual_output_dir}")
    return actual_output_dir
