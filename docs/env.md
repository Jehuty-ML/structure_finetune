# Environment setup

Python **3.10+** recommended.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate

# Optional: install CUDA-matched PyTorch first (see comments in requirements.txt)
pip install -r requirements.txt
```

Or with conda:

```bash
conda env create -f environment.yml
conda activate structured-llm
```

Contract validation and `--mode fixture` eval only need the lighter packages (`PyYAML`, `jsonschema`) and can run without a GPU. Full SFT needs CUDA + the Unsloth stack from `requirements.txt`.
