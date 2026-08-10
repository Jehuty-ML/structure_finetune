from __future__ import annotations

from pathlib import Path
from typing import Any


def load_yaml(path: str | Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise ImportError("PyYAML is required: pip install pyyaml") from exc
    with Path(path).open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"config must be a mapping: {path}")
    return data


def run_sft(config: dict[str, Any]) -> Path:
    """
    SFT entry point.

    When config['dry_run'] is true (default in the sample config), only verify
    that training rows pass the contract — no GPU required.

    Wire Unsloth / PEFT + TRL here for a real run (see docs/train.md).
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
            print(f"[INVALID] {row.get('id')}: {result.errors}")

    if bad:
        raise SystemExit(f"{bad}/{n} training rows failed contract validation")
    print(f"Contract check passed for {n} rows.")

    if config.get("dry_run", True):
        print("dry_run=true - skipping GPU SFT. Set dry_run: false and implement Unsloth/PEFT.")
        (output_dir / "DRY_RUN.txt").write_text(
            "Replace run_sft() body with Unsloth/PEFT training.\n", encoding="utf-8"
        )
        return output_dir

    raise NotImplementedError(
        "Real SFT is intentionally left as an integration point. "
        "Implement Unsloth/PEFT loading using config keys "
        "(model_name_or_path, lora_*, learning_rate, ...)."
    )
