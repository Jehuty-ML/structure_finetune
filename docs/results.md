# 评测结果（Echo 契约 v3）

实验日期：2026-08-11  

| 项目 | 取值 |
|------|------|
| 基座 | Qwen3-1.7B（ModelScope 本地） |
| 契约 | v3：`<think>` → `[json]…[/json]` |
| SFT | LoRA r=16，含多轮 Prior 样本，3 epoch |
| Adapter | `outputs/echo_lora/Qwen3-1.7B_r16_len2048_lr2e-4_0811_1043` |
| 评测集 | `examples/echo/eval_cases.json`（疲惫 / 静音 / 多轮承接） |

## 对比：Prompt-only vs SFT

| 设置 | 通过率 | 格式合法率 | Schema 合法率 | TTS 安全率 |
|------|--------|------------|---------------|------------|
| 基座 + 系统提示 | **33.3%** | 33.3% | 33.3% | 66.7% |
| 基座 + LoRA | **100%** | 100% | 100% | 100% |

命令：

```bash
python scripts/evaluate.py --mode generate --compare `
  --base-model Qwen/Qwen3-1.7B `
  --adapter outputs/echo_lora/Qwen3-1.7B_r16_len2048_lr2e-4_0811_1043 `
  --json-out outputs/eval_compare_v3.json
```

## 解读

- **基座**仍会写出非法枚举（如 `calm|neutral`），格式焊不稳。
- **SFT** 三例全过：疲惫韵律、静音 `text_only`、多轮「搬家 → 离开朋友」承接。
- 多轮样本 + 训推统一 `Prior` 行后，内容承接从失败变为通过。

原始 JSON：`outputs/eval_compare_v3.json`。
