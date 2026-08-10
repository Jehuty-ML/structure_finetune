from __future__ import annotations

from pathlib import Path
from typing import Any


def load_yaml(path: str | Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise ImportError("需要 PyYAML：pip install pyyaml") from exc
    with Path(path).open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"配置必须是映射（mapping）：{path}")
    return data


def run_sft(config: dict[str, Any]) -> Path:
    """
    SFT 入口。

    当 config['dry_run'] 为 true（样例配置默认）时，仅校验训练行是否符合契约，无需 GPU。

    真实训练请在此接入 Unsloth / PEFT + TRL（见 docs/train.md）。
    """
    from structured_llm.contract import validate_turn
    from structured_llm.data import iter_sft_rows

    data_path = Path(config["data_path"])
    schema_path = Path(config.get("schema_path", "schemas/echo_turn.schema.json"))
    output_dir = Path(config.get("output_dir", "outputs/echo_lora"))
    output_dir.mkdir(parents=True, exist_ok=True)

    bad = 0
    n = 0
    for row in iter_sft_rows(data_path):
        n += 1
        result = validate_turn(row["output"], schema_path=schema_path)
        if not result.ok:
            bad += 1
            print(f"[无效] {row.get('id')}: {result.errors}")

    if bad:
        raise SystemExit(f"{bad}/{n} 条训练数据未通过契约校验")
    print(f"契约检查通过，共 {n} 条。")

    if config.get("dry_run", True):
        print("dry_run=true，跳过 GPU SFT。将 dry_run 设为 false 并实现 Unsloth/PEFT。")
        (output_dir / "DRY_RUN.txt").write_text(
            "请将 run_sft() 主体替换为 Unsloth/PEFT 训练逻辑。\n", encoding="utf-8"
        )
        return output_dir

    raise NotImplementedError(
        "真实 SFT 刻意留作接入点。"
        "请使用配置项（model_name_or_path、lora_*、learning_rate 等）实现 Unsloth/PEFT 加载与训练。"
    )
