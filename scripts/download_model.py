#!/usr/bin/env python3
"""从 ModelScope 下载基座模型到 models/base（不走 HuggingFace）。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from structured_llm.train.model_source import resolve_model_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model",
        default="Qwen/Qwen3-1.7B",
        help="ModelScope 模型 ID，如 Qwen/Qwen3-1.7B",
    )
    parser.add_argument(
        "--cache-dir",
        default="models/base",
        help="相对仓库根目录的缓存目录",
    )
    parser.add_argument(
        "--local-only",
        action="store_true",
        help="只查本地缓存，不联网下载",
    )
    args = parser.parse_args()

    path = resolve_model_path(
        args.model,
        project_root=ROOT,
        source="modelscope",
        local_files_only=args.local_only,
        cache_subdir=args.cache_dir,
    )
    print(path)


if __name__ == "__main__":
    main()
