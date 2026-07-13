
# PMM Codex Skills

用于沉淀和分发 PMM 场景下可复用的 Codex Skills。

## Skills

| Skill | 用途 |
| --- | --- |
| [`logo-wall-layout`](./logo-wall-layout) | 按飞书标品规范制作、排版、审查和修改 Logo 墙，支持深浅背景、公开/闭门场景、Logo 排序、网格布局及多格式交付。 |
| [`logo-standardize`](./logo-standardize) | 将 PDF、AI、PNG 等 Logo 源文件标准化为统一的白底圆角 PNG，适用于 Logo 墙素材与品牌展示资产。 |

## 安装

### 安装 Logo 墙排版 Skill

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo irisivy7421-ux/pmm-skills \
  --path logo-wall-layout
```

### 安装 Logo 标准化 Skill

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo irisivy7421-ux/pmm-skills \
  --path logo-standardize
```

## 使用示例

安装完成后，可以直接向 Codex 提出需求：

- “用 `logo-wall-layout` 制作一面深色、公开场合使用的客户 Logo 墙。”
- “用 `logo-standardize` 将这个 PDF 中的 Logo 标准化为白底圆角 PNG。”

> Skill 安装后将在下一轮对话中生效。
```
