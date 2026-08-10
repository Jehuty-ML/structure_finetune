# 阶段 4：真机对话演示

目标：证明训好的小模型能接到产品链路——

```text
你输入 → LoRA 真实生成 → validate_turn → voice / 假 TTS 字段
```

不是起一个只吃假 `raw` 的 HTTP。

---

## 主入口

```bash
# 交互聊天
python scripts/chat_echo.py `
  --adapter outputs/echo_lora/Qwen3-1.7B_r16_len2048_lr2e-4_0811_1043

# 固定四句验收（疲惫 / 静音 / 搬家→离开朋友）
python scripts/chat_echo.py `
  --adapter outputs/echo_lora/Qwen3-1.7B_r16_len2048_lr2e-4_0811_1043 `
  --accept
```

需要 GPU，以及已装 Unsloth 的环境（如 `llm_dev`）。

交互命令：`mute` 切换静音开关，`quit` 退出。  
含「图书馆 / 静音」等关键词的句子会自动 `can_speak=false`。

每轮打印：

| 块 | 含义 |
|----|------|
| raw | 模型原始多块文本 |
| voice | 给 App 的完整契约对象 |
| 假 TTS | 只取 utter / emotion / volume / pace / should_speak |

实现：`src/structured_llm/serve/chat.py`（回合）+ `response.py`（解析 / 假 TTS）。

---

## 与阶段 3 的区别

| | 阶段 3 `evaluate --mode generate` | 阶段 4 `chat_echo` |
|--|--|--|
| 目的 | 固定评测集打分 | 真聊 / 验收演示 |
| 输入 | `eval_cases.json` | 终端或 `--accept` 脚本 |
| 对比基座 | 支持 `--compare` | 通常只挂 LoRA |

解析器相同：都是 `validate_turn`。

---

## 附录：无 GPU 只测解析

```bash
pip install -r requirements-min.txt
python scripts/serve_api.py --port 8000
python scripts/smoke_serve.py
```

仅验证解析 API，**不能**替代 `--accept` 真机验收。
