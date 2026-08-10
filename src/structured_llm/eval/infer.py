"""本地推理：基座 / 基座+LoRA，供契约评测 generate 模式使用。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional


def make_generate_fn(
    *,
    project_root: Path,
    base_model: str,
    adapter: Optional[str] = None,
    max_seq_length: int = 2048,
    max_new_tokens: int = 512,
    temperature: float = 0.3,
    load_in_4bit: bool = True,
) -> Callable[[str, str], str]:
    """
    返回 generate_fn(system_prompt, user_message) -> assistant_text。
    默认从 ModelScope/本地解析基座；adapter 为 LoRA 目录时可叠加。
    """
    from structured_llm.train.model_source import resolve_model_path
    from structured_llm.train.sft_unsloth import _setup_env

    _setup_env(project_root)

    import os

    resolved_base = resolve_model_path(
        base_model,
        project_root=project_root,
        source="modelscope" if not Path(base_model).exists() else "local",
        local_files_only=Path(base_model).exists(),
    )
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

    import torch
    from unsloth import FastLanguageModel

    print(f"评测加载基座：{resolved_base}")
    dtype = (
        torch.bfloat16
        if torch.cuda.is_available() and torch.cuda.is_bf16_supported()
        else None
    )
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=resolved_base,
        max_seq_length=max_seq_length,
        dtype=dtype,
        load_in_4bit=load_in_4bit,
        local_files_only=True,
    )

    if adapter:
        adapter_path = Path(adapter)
        if not (adapter_path / "adapter_config.json").exists():
            raise FileNotFoundError(f"未找到 LoRA adapter：{adapter}")
        print(f"加载 LoRA：{adapter_path}")
        model.load_adapter(str(adapter_path), adapter_name="echo_lora")
        model.set_adapter("echo_lora")

    FastLanguageModel.for_inference(model)

    def generate_fn(system_prompt: str, user_message: str) -> str:
        prompt = (
            f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
            f"<|im_start|>user\n{user_message}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )
        inputs = tokenizer([prompt], return_tensors="pt").to(model.device)
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=0.9,
                top_k=20,
                do_sample=temperature > 0,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id,
                use_cache=True,
            )
        full = tokenizer.decode(outputs[0], skip_special_tokens=False)
        if "<|im_start|>assistant\n" in full:
            text = full.split("<|im_start|>assistant\n")[-1]
            if "<|im_end|>" in text:
                text = text.split("<|im_end|>")[0]
            return text.strip()
        # 退化：去掉 prompt 前缀
        decoded = tokenizer.batch_decode(
            outputs[:, inputs["input_ids"].shape[1] :], skip_special_tokens=True
        )[0]
        return decoded.strip()

    return generate_fn
