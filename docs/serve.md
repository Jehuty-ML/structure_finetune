# 阶段 4：真机对话演示

目标：证明训好的小模型能接到产品链路——

```text
你输入 → LoRA 真实生成 → 契约解析 → 下游只吃字段
```

不是起一个只吃假 `raw` 的 HTTP。

---

## Echo（语音）

```bash
# 交互聊天
python scripts/chat_echo.py `
  --adapter outputs/echo_lora/Qwen3-1.7B_r16_len2048_lr2e-4_0811_1043

# 固定验收（疲惫 / 静音 / 搬家→离开朋友）
python scripts/chat_echo.py `
  --adapter outputs/echo_lora/Qwen3-1.7B_r16_len2048_lr2e-4_0811_1043 `
  --accept
```

交互命令：`mute` 切换静音，`quit` 退出。  
每轮打印：`raw` / `voice` / 假 TTS。

实现：`serve/chat.py` → `run_echo_turn` + `validate_turn`。

---

## Quest（RPG）

```bash
# 先训（examples/quest/configs/sft_lora.yaml 中 dry_run: false）
python scripts/train.py --config examples/quest/configs/sft_lora.yaml

# 交互
python scripts/chat_quest.py --adapter outputs/quest_lora/<run_dir>

# 验收：探索路口 / 遇敌 / 逃跑
python scripts/chat_quest.py --adapter outputs/quest_lora/<run_dir> --accept
```

交互命令：`status` 看 fsm/stats，`reset` 重置，`quit` 退出。  
每轮打印：`raw` / state·cmd·stats / say / abstract / 假引擎。

实现：`run_quest_turn` + `validate_quest_turn`；会话会用输出更新下一拍的 `fsm`/`stats`。

评测（无 GPU fixture）：

```bash
python scripts/evaluate.py --contract quest --mode fixture
```

---

## 与阶段 3 的区别

| | 阶段 3 `evaluate --mode generate` | 阶段 4 `chat_*` |
|--|--|--|
| 目的 | 固定评测集打分 | 真聊 / 验收演示 |
| 输入 | `eval_cases.json` | 终端或 `--accept` |
| 对比基座 | 支持 `--compare` | 通常只挂 LoRA |

---

## 附录：无 GPU 只测解析

```bash
pip install -r requirements-min.txt
python scripts/serve_api.py --port 8000
python scripts/smoke_serve.py
```

仅验证 Echo 解析 API，**不能**替代 `--accept` 真机验收。
