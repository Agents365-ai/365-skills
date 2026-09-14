# 已知限制

[← 返回 README](https://github.com/Agents365-ai/365-skills/blob/main/plugins/tldraw/README_CN.md)

- **原生 UML 标记**:tldraw 可渲染实心 `triangle`/`diamond` 箭头(用于继承/组合*草图*足够),但不支持严格 UML 所用的*空心*箭头。学术论文级 UML/ERD 图请使用 drawio-skill
- **泳道 / 嵌套自动布局**:tldraw *确实*有原生 `frame` 容器(带标题的盒子,可嵌入形状,堆叠可近似泳道),但容器*内部*没有自动布局——子形状位置仍需手工摆放。需要 drawio 式带自动排布的泳道池,请使用 drawio-skill
- **不支持 PDF 导出**:tldraw-cli 仅支持 PNG 和 SVG。如需 PDF,可将 SVG 后处理转换(如 `rsvg-convert`)
- **自检需要视觉能力**:自动修复步骤通过模型的视觉能力读取 PNG。不支持视觉的模型会跳过此步
