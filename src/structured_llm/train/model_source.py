"""模型来源：默认 ModelScope，避免依赖 HuggingFace 下载。"""

from __future__ import annotations

import os
from pathlib import Path


def _looks_like_model_dir(path: Path) -> bool:
    if not (path / "config.json").exists():
        return False
    # 至少有分片索引或单文件权重
    if (path / "model.safetensors").exists():
        return True
    if (path / "model.safetensors.index.json").exists():
        # 索引存在还不够，需要至少有一个分片
        return bool(list(path.glob("*.safetensors")))
    if (path / "pytorch_model.bin").exists():
        return True
    if list(path.glob("*.safetensors")):
        return True
    return False


def resolve_model_path(
    model_id_or_path: str,
    *,
    project_root: Path,
    source: str = "modelscope",
    local_files_only: bool = False,
    cache_subdir: str = "models/base",
) -> str:
    """
    将配置中的模型 ID / 路径解析为本地目录。

    - 若已是本地目录且含权重，直接返回
    - source=modelscope：用 snapshot_download 拉到 project_root/models/base
    - source=local：要求路径已存在
    - source=huggingface：不推荐（国内常超时）；仅透传 ID
    """
    raw = Path(model_id_or_path)
    if raw.exists() and _looks_like_model_dir(raw):
        return str(raw.resolve())

    source = (source or "modelscope").lower()
    if source in ("local", "path"):
        raise FileNotFoundError(
            f"本地模型不存在或不完整：{model_id_or_path}"
        )

    if source in ("hf", "huggingface"):
        print("警告：source=huggingface，国内常超时；建议改用 modelscope。")
        return model_id_or_path

    cache_dir = project_root / cache_subdir
    cache_dir.mkdir(parents=True, exist_ok=True)

    # ModelScope 默认缓存：Qwen3-1.7B -> Qwen3-1___7B
    ms_hub = Path.home() / ".cache" / "modelscope" / "hub" / "models"
    dotted = model_id_or_path.replace(".", "___").replace("/", os.sep)
    plain = model_id_or_path.replace("/", os.sep)
    candidates = [
        ms_hub / dotted,
        ms_hub / plain,
        cache_dir / plain,
        cache_dir / dotted,
    ]
    for candidate in candidates:
        if candidate.exists() and _looks_like_model_dir(candidate):
            print(f"使用已有 ModelScope/本地缓存：{candidate}")
            return str(candidate.resolve())

    if local_files_only:
        raise FileNotFoundError(
            f"local_files_only=true 且未找到完整本地模型：{model_id_or_path}"
        )

    try:
        from modelscope import snapshot_download
    except ImportError as exc:
        raise ImportError("需要 modelscope：pip install modelscope") from exc

    print(f"从 ModelScope 下载：{model_id_or_path} -> {cache_dir}")
    path = snapshot_download(
        model_id=model_id_or_path,
        cache_dir=str(cache_dir),
        local_files_only=False,
    )
    print(f"ModelScope 就绪：{path}")
    return str(Path(path).resolve())
