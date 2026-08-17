# GitHub 发布打磨清单

仓库：https://github.com/Jehuty-ML/structure_finetune

## About 用英文还是中文？

- **Topics** 几乎全是英文标签（`llm`、`fine-tuning`…），用英文才进得了 GitHub 搜索与相关仓库推荐。
- **About** 一句话会出现在仓库卡片、搜索结果、社交分享上，面向「逛 GitHub 的人」时英文覆盖面更大。
- README 可以继续以中文为主；About 与正文不必同一语言。

若更在意国内读者一眼看懂，可改用下面的中文 About（Topics 仍建议保留英文）。

## About / Topics（可用 `gh`）

英文（推荐，利于发现）：

```bash
gh repo edit Jehuty-ML/structure_finetune `
  --description "SFT small LLMs (1.7B–8B) into a fixed output contract for TTS / UI / game engines. Demos: Echo (voice), Quest (RPG)." `
  --add-topic llm `
  --add-topic fine-tuning `
  --add-topic sft `
  --add-topic lora `
  --add-topic structured-output `
  --add-topic json-schema `
  --add-topic digital-human `
  --add-topic game-ai
```

中文（可选）：

```bash
gh repo edit Jehuty-ML/structure_finetune `
  --description "把小模型 SFT 成固定输出契约，对接 TTS / UI / 游戏引擎。Demo：Echo（语音）、Quest（RPG）。"
```

## Social preview 图

素材（1280×640）：

- PNG（可直接上传）：[`docs/assets/social-preview.png`](assets/social-preview.png)
- SVG（可再编辑）：[`docs/assets/social-preview.svg`](assets/social-preview.svg)

GitHub 网页设置路径：

1. Repo → **Settings** → **General** → **Social preview**
2. 上传 `social-preview.png`
3. 保存后，分享链接卡片会显示该图

> API 无法直接上传 Social preview 图，需在网页完成一次。  
> `gh repo edit` 可改 description / topics（需先 `gh auth login`）。

## README 首屏检查

- [ ] 定位图 / 结果条 / 终端示意在 GitHub 上渲染正常  
- [ ] Topics 与 description 已设置  
- [ ] Social preview 已上传  
