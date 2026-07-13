# 使用示例

## 基础用法

```bash
python3 scripts/process_logo.py input.ai output.png
```

## PNG 作为源文件

```bash
python3 scripts/process_logo.py input_logo.png output.png
```

## 指定参数

```bash
python3 scripts/process_logo.py input.ai output.png --zoom 10 --canvas-width 2000 --canvas-height 1000 --safe-width 1600 --safe-height 680 --radius 100
```

## 图标+中英文上下叠排组合

当参考图或人工判断确认 Logo 是图标+英文+中文上下叠排组合时，即使内容宽高比落在 `1.25~4.0` 的常规区间，也应按方形规则以高度 `680 px` 处理：

```bash
python3 scripts/process_logo.py input.ai output.png --force-square
```

## 典型处理流程

先用 `file` 查看输入文件格式；若 `.ai` 实际为 PDF-compatible 文件，则直接运行脚本。脚本会输出裁边后尺寸、宽高比、形态分类、最终放置尺寸、位置与 alpha extrema。

## 参考截图介入的场景

如果 AI 文件中除了 Logo 主体，还混有色卡、辅助线或说明元素，而用户同时给了“正确 Logo 范围”的参考截图，不要直接把自动裁边结果当作最终画面。应先根据参考截图确认真实范围，必要时先人工裁干净输入，再执行脚本。

## 结果自检

至少检查以下几项：

- 输出尺寸是否为 `2000 × 1000`
- alpha extrema 是否显示存在透明圆角
- 输出文件是否落在 `90–140 KB`
- 偏方形、细长型、常规型 Logo 是否进入了正确分支
