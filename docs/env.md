# 环境搭建

建议使用 Python **3.10+**。

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate

# 可选：先安装与 CUDA 匹配的 PyTorch（见 requirements.txt 注释）
pip install -r requirements.txt
```

或使用 conda：

```bash
conda env create -f environment.yml
conda activate structured-llm
```

契约校验与 `--mode fixture` 评测只需较轻依赖（`PyYAML`、`jsonschema`），无 GPU 也可跑。完整 SFT 需要 CUDA，以及 `requirements.txt` 中的 Unsloth 相关栈。
