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


def _gate_contract(config: dict[str, Any]) -> int:
    """无合格数据不开真训：训练前强制契约门禁。"""
    from structured_llm.contract import validate_turn
    from structured_llm.data import iter_sft_rows

    data_path = Path(config["data_path"])
    schema_path = Path(config.get("schema_path", "schemas/echo_turn.schema.json"))
    bad = 0
    n = 0
    for row in iter_sft_rows(data_path):
        n += 1
        result = validate_turn(
            row["output"],
            schema_path=schema_path,
            input_obj=row["input"] if isinstance(row.get("input"), dict) else None,
        )
        if not result.ok:
            bad += 1
            print(f"[无效] {row.get('id')}: {result.errors}")
    if bad:
        raise SystemExit(f"{bad}/{n} 条训练数据未通过契约校验，已中止训练")
    print(f"契约门禁通过，共 {n} 条。")
    return n


def run_sft(config: dict[str, Any], project_root: Path | None = None) -> Path:
    """
    SFT 入口。

    1) 先做契约门禁（阶段 1）
    2) dry_run=true 时到此结束
    3) dry_run=false 时走 Unsloth 真训（阶段 2）
    """
    output_dir = Path(config.get("output_dir", "outputs/echo_lora"))
    output_dir.mkdir(parents=True, exist_ok=True)
    _gate_contract(config)

    if config.get("dry_run", True):
        print("dry_run=true，跳过 GPU SFT。将配置改为 dry_run: false 以启动真训。")
        (output_dir / "DRY_RUN.txt").write_text(
            "契约已通过。设置 dry_run: false 后将调用 Unsloth SFT。\n",
            encoding="utf-8",
        )
        return output_dir

    root = project_root or Path.cwd()
    from structured_llm.train.sft_unsloth import run_unsloth_sft

    return run_unsloth_sft(config, root)
