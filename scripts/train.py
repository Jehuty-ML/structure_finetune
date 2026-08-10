#!/usr/bin/env python3
"""SFT entry — validates contract then optionally runs training."""

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
        default=str(ROOT / "examples" / "echo" / "configs" / "sft_lora.yaml"),
    )
    args = parser.parse_args()

    os.chdir(ROOT)
    config = load_yaml(args.config)
    out = run_sft(config)
    print(f"output_dir={out}")


if __name__ == "__main__":
    main()
