# GitHub 发布打磨清单

仓库：https://github.com/Jehuty-ML/structure_finetune

## About / Topics（可用 `gh`）

```bash
gh repo edit Jehuty-ML/structure_finetune `
  --description "SFT small LLMs into a fixed output contract — Echo (voice) & Quest (RPG). Not prompt lottery." `
  --homepage "" `
  --add-topic llm `
  --add-topic fine-tuning `
  --add-topic sft `
  --add-topic lora `
  --add-topic structured-output `
  --add-topic json-schema `
  --add-topic digital-human `
  --add-topic game-ai
```

建议英文一句话（About）：

> SFT small LLMs (1.7B–8B) into a fixed output contract for TTS / UI / game engines. Demos: Echo (voice), Quest (RPG).

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
