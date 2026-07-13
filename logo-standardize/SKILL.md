---
name: logo-standardize
description: 将 .ai、.pdf 等 Logo 源文件标准化导出为统一白底圆角 PNG，支持格式探测、双重裁边、按内容宽高比分流缩放、真实透明圆角和 PNG 体积控制。适用于制作 Logo 墙素材、品牌展示素材、白底标准化资产，尤其适合处理 PDF-compatible AI 文件、需要统一视觉重量的多品牌 Logo，或用户提供参考截图以辅助确认 Logo 真实画面范围的场景。
author: sunjing.iris
---

# logo-standardize

用于把单个 Logo 源文件整理成统一规格的白底圆角 PNG。默认输出为 `2000×1000 px`，版心为 `1600×680 px`，圆角半径 `100 px`，目标体积 `90–140 KB`。

## 快速路径（多页 PDF / 有参考截图时优先）

1. 先用低清分页预览定位页码：`python3 scripts/preview_pdf_pages.py input.pdf preview.png`。
2. 根据参考截图只选择一个页面和目标区域；不要高分辨率渲染整份 PDF。
3. 再标准化：`python3 scripts/process_logo.py input.pdf output.png --page 2 --crop 0.12,0.15,0.40,0.46 --force-square`。

`--crop` 为相对页宽高的 `x,y,width,height`，用于排除同页的其他语言版本、说明文字和色卡。脚本优先使用 PyMuPDF；不可用时自动回退到 Poppler (`pdftoppm`)。

## 适用场景

在以下场景使用本 Skill：

- 将 `.ai`、`.pdf` 等矢量 Logo 源文件，或用户直接提供的 `.png` Logo 源文件，导出为标准白底 PNG
- 为 Logo 墙或品牌素材库准备统一规格的 Logo 砖块
- 需要不同 Logo 在统一容器中保持接近的视觉重量
- 需要真实透明圆角，而不是伪造白角
- AI 原文件不够干净，且用户提供了参考截图，需要据此确认真实 Logo 范围

## 默认参数

- 画布：`2000 × 1000 px`
- 版心：`1600 × 680 px`
- 圆角半径：`100 px`
- 常规主视觉高度：`400 px`
- 文件大小目标：`90–140 KB`

## 执行步骤

### 1. 判断输入格式

先用 `file` 命令确认输入文件真实格式，而不是只依赖扩展名。对于 PDF-compatible 的 `.ai` 文件，优先走 PyMuPDF (`fitz`) 渲染路径；如果用户提供的是 `.png`，且这张 PNG 本身就是唯一的 Logo 源文件，则直接把 PNG 作为输入继续处理。

### 2. 读取源文件

使用 `scripts/process_logo.py` 读取源文件。对于矢量文件，脚本只渲染选定页面，默认倍率为 `zoom=6`；对于 PNG 源文件，脚本会直接读取该 PNG，并进入与矢量文件相同的后续流程。

### 3. 做内容裁边

内容边界要结合两类信息一起判断：

- 合成到白底后的非白像素
- 原图中的 alpha 非透明区域

执行两次裁边，先裁掉大块空白，再去掉残余近白边缘。用户直接提供 PNG 作为源文件时，也按同样规则裁掉白边与无关留白，再进入后续形态判断和缩放。

### 4. 判断 Logo 形态并缩放

形态判断依据是**内容区域**的宽高比，也就是裁边后的内容包围盒宽高比：`ratio = 内容区域宽度 / 内容区域高度`。

按以下规则分流：

- `ratio < 1.25`：视为偏方形 Logo，高度对齐到 `680 px`
- `ratio > 4.0`：视为细长型 Logo，宽度对齐到 `1600 px`
- `1.25 ≤ ratio ≤ 4.0`：视为常规型 Logo，以主视觉高度约 `400 px` 为基准，并限制不得超出版心
- 当 Logo 为图标+中英文上下叠排组合时，即使宽高比在 `1.25~4.0` 之间，也应优先按方形规则以高度 `680 px` 处理，而非常规型的 `400 px`，以保证视觉重量足够

先裁边，再判断比例。不要用原始画布外框比例代替内容比例，否则空白边和辅助元素会干扰形态判断。遇到图标+中英文上下叠排这类视觉更接近“块状”的组合 Logo 时，以组合结构优先于单纯宽高比判断。

### 5. 处理不干净的 AI 文件

如果 AI 文件里除了 Logo 主体，还混有色卡、辅助线、标注或其他非正式出图元素，而用户同时提供了 Logo 范围参考截图，则以**参考截图**为准确认真实画面范围。

这类情况下，不要机械依赖原文件自动检测出的全部内容边界。先根据参考截图排除色卡等非 Logo 内容，再继续后续缩放、居中与圆角处理。必要时先手动裁干净输入，再运行脚本。

### 6. 居中合成到白底画布

创建 `RGBA(255,255,255,255)` 的白底画布，将缩放后的 Logo 居中放置，并通过 `alpha_composite` 合成。

### 7. 应用真实透明圆角

使用 `ImageDraw.rounded_rectangle` 生成 `L` 模式圆角 mask，再用 `putalpha` 应用到整张图。不要通过绘制白色角块伪造圆角。

### 8. 控制文件大小并校验

导出 PNG 时使用高压缩；如果体积低于目标下限，可通过 PNG metadata padding 做补足。若按方形规则放大后体积超过上限，可使用保留平面品牌色与 alpha 圆角的调色板量化降低体积。导出后校验尺寸、alpha 和文件体积。

## 脚本与参考资料

- 执行脚本：`scripts/process_logo.py`
- 算法说明：`[algorithm-notes.md](references/algorithm-notes.md)`
- 使用示例：`[examples.md](references/examples.md)`

## 运行方式

在 Skill 根目录下执行：

```bash
python3 scripts/process_logo.py input.ai output.png
```

如果源文件本身就是 PNG：

```bash
python3 scripts/process_logo.py input_logo.png output.png
```

可选参数：

```bash
python3 scripts/process_logo.py input.ai output.png --page 2 --crop 0.12,0.15,0.40,0.46 --zoom 6 --canvas-width 2000 --canvas-height 1000 --safe-width 1600 --safe-height 680 --radius 100
```

若已根据参考图确认 Logo 属于图标+中英文上下叠排组合，即使裁边后宽高比落在常规区间，也按方形规则处理：

```bash
python3 scripts/process_logo.py input.ai output.png --force-square
```

## 注意事项

- 以内容区域而不是原始画布判断 Logo 形态
- AI 文件不干净且有参考截图时，以参考截图确认保留范围
- 圆角必须通过 alpha mask 实现，保证后续叠加时边缘真实透明
- 目标是统一视觉重量，不是让所有 Logo 机械撑满版心
- 图标+中英文上下叠排组合 Logo 应按方形规则拉到 `680 px` 高度，避免被常规 `400 px` 规则压得过小
- 若用户要求保留某些特殊留白或边界，应优先遵从用户口径，再调整裁边策略
