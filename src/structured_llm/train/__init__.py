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
    from structured_llm.contract import validate_quest_turn, validate_turn
    from structured_llm.data import iter_sft_rows

    data_path = Path(config["data_path"])
    contract = str(config.get("contract", "echo")).lower()
    schema_path = Path(config.get("schema_path", "schemas/echo_turn.schema.json"))
    bad = 0
    n = 0
    for row in iter_sft_rows(data_path):
        n += 1
        inp = row["input"] if isinstance(row.get("input"), dict) else None
        if contract == "quest":
            result = validate_quest_turn(row["output"], input_obj=inp)
        else:
            result = validate_turn(
                row["output"],
                schema_path=schema_path,
                input_obj=inp,
            )
        if not result.ok:
            bad += 1
            print(f"[无效] {row.get('id')}: {result.errors}")
    if bad:
        raise SystemExit(f"{bad}/{n} 条训练数据未通过契约校验，已中止训练")
    print(f"契约门禁通过（contract={contract}），共 {n} 条。")
    return n


def _gate_preference(config: dict[str, Any]) -> int:
    """DPO 门禁：chosen 必须过契约；rejected 仅做非空与不等于 chosen 检查。"""
    from structured_llm.contract import validate_quest_turn, validate_turn
    from structured_llm.data import iter_dpo_rows

    data_path = Path(config["data_path"])
    contract = str(config.get("contract", "echo")).lower()
    schema_path = Path(config.get("schema_path", "schemas/echo_turn.schema.json"))
    require_rejected_valid = bool(config.get("require_rejected_valid", False))
    bad = 0
    n = 0
    for row in iter_dpo_rows(data_path):
        n += 1
        inp = row["input"] if isinstance(row.get("input"), dict) else None
        chosen = str(row["chosen"])
        rejected = str(row["rejected"])
        if not chosen.strip() or not rejected.strip():
            bad += 1
            print(f"[无效] {row.get('id')}: chosen/rejected 为空")
            continue
        if chosen == rejected:
            bad += 1
            print(f"[无效] {row.get('id')}: chosen == rejected")
            continue
        if contract == "quest":
            result = validate_quest_turn(chosen, input_obj=inp)
        else:
            result = validate_turn(chosen, schema_path=schema_path, input_obj=inp)
        if not result.ok:
            bad += 1
            print(f"[无效 chosen] {row.get('id')}: {result.errors}")
            continue
        if require_rejected_valid:
            if contract == "quest":
                rr = validate_quest_turn(rejected, input_obj=inp)
            else:
                rr = validate_turn(rejected, schema_path=schema_path, input_obj=inp)
            if not rr.ok:
                bad += 1
                print(f"[无效 rejected] {row.get('id')}: {rr.errors}")
    if bad:
        raise SystemExit(f"{bad}/{n} 条偏好数据未通过门禁，已中止 DPO")
    print(f"偏好门禁通过（contract={contract}），共 {n} 对。")
    return n


def run_sft(config: dict[str, Any], project_root: Path | None = None) -> Path:
    """
    SFT 入口。

    1) 先做契约门禁（阶段 1）
    2) dry_run=true 时到此结束
    3) dry_run=false 时走 Unsloth 真训（阶段 2）
    """
    default_out = (
        "outputs/quest_lora"
        if str(config.get("contract", "echo")).lower() == "quest"
        else "outputs/echo_lora"
    )
    output_dir = Path(config.get("output_dir", default_out))
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


def run_dpo(config: dict[str, Any], project_root: Path | None = None) -> Path:
    """
    DPO 入口。

    1) 偏好门禁（chosen 契约必过）
    2) dry_run=true 时到此结束
    3) dry_run=false 时走 Unsloth + TRL DPOTrainer
    """
    default_out = (
        "outputs/quest_dpo"
        if str(config.get("contract", "echo")).lower() == "quest"
        else "outputs/echo_dpo"
    )
    output_dir = Path(config.get("output_dir", default_out))
    output_dir.mkdir(parents=True, exist_ok=True)
    _gate_preference(config)

    if config.get("dry_run", True):
        print("dry_run=true，跳过 GPU DPO。将配置改为 dry_run: false 以启动真训。")
        (output_dir / "DRY_RUN.txt").write_text(
            "偏好门禁已通过。设置 dry_run: false 后将调用 Unsloth DPO。\n",
            encoding="utf-8",
        )
        return output_dir

    root = project_root or Path.cwd()
    from structured_llm.train.dpo_unsloth import run_unsloth_dpo

    return run_unsloth_dpo(config, root)
