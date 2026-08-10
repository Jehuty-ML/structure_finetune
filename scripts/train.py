#!/usr/bin/env python3
"""SFT 入口：先校验契约，再按需启动训练。"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from structured_llm.train import load_yaml, run_sft


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default=str(ROOT / "examples" / "quest" / "configs" / "sft_lora.yaml"),
        help="训练配置 YAML 路径",
    )
    args = parser.parse_args()

    os.chdir(ROOT)
    config = load_yaml(args.config)
    out = run_sft(config, project_root=ROOT)
    print(f"输出目录={out}")


if __name__ == "__main__":
    main()
