# excalidraw-skill —— 自然语言生成简洁 / 手绘风格图表

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/Agents365-ai/excalidraw-skill?style=flat&logo=github&cacheSeconds=86400)](https://github.com/Agents365-ai/excalidraw-skill/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/Agents365-ai/excalidraw-skill?style=flat&logo=github&cacheSeconds=86400)](https://github.com/Agents365-ai/excalidraw-skill/network/members)
[![Latest Release](https://img.shields.io/github/v/release/Agents365-ai/excalidraw-skill?logo=github&cacheSeconds=86400)](https://github.com/Agents365-ai/excalidraw-skill/releases/latest)
[![Last Commit](https://img.shields.io/github/last-commit/Agents365-ai/excalidraw-skill?logo=github&cacheSeconds=3600)](https://github.com/Agents365-ai/excalidraw-skill/commits/main)

[![SkillsMP](https://img.shields.io/badge/SkillsMP-listed-1f6feb)](https://skillsmp.com/skills/agents365-ai-excalidraw-skill-skills-excalidraw-skill-skill-md)
[![ClawHub](https://img.shields.io/badge/ClawHub-listed-ff6b35)](https://clawhub.ai/agents365-ai/excalidraw-skill)
[![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-plugin-8a2be2)](https://github.com/Agents365-ai/365-skills)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-兼容-2ea44f)](https://agentskills.io)
[English](README.md) · **中文** · [📖 在线文档](https://agents365-ai.github.io/excalidraw-skill/zh.html)

一个把自然语言描述变成简洁、专业的 `.excalidraw` JSON(需要时也能出手绘风格草图),并导出为 PNG / SVG 的技能 —— 既可走零安装的 [Kroki](https://kroki.io) API,也可走本地 [`excalidraw-brute-export-cli`](https://www.npmjs.com/package/excalidraw-brute-export-cli)。支持 **Claude Code、Cursor、Copilot、OpenClaw、Codex、Hermes** 等任何兼容 [Agent Skills](https://agentskills.io) 规范的 agent。

<p align="center">
  <img src="assets/microservices-example.png" width="900" alt="微服务架构图 —— 来自一条自然语言提示词">
</p>

## ✨ 核心亮点

- **内置设计体系** —— 8 类语义配色、5 级字号层级,遵循 60-30-10 留白法则
- **5 种图表模式** —— 流程图、架构图、时序图、思维导图、泳道图,每种都有专属布局与间距规则
- **3 种箭头路由** —— 直线、L 形折线、曲线 waypoint,连线干净不打结
- **CJK 智能尺寸** —— 按标签自动算宽度(`max(160, charCount × 9)`,CJK 字符翻倍),标签不再被截
- **反模式防护** —— 短箭头标签碰撞、区域文字重叠、面条箭头、容器透明度等坑都在 SKILL.md 中提前避开
- **200+ 社区图标库** —— 把真实的 AWS / Azure / GCP / 网络 / UML / BPMN 图标直接放进图里(它们是矢量的,能走导出路径渲染),由内置脚本一键嵌入
- **两种导出后端** —— `curl` 走 Kroki(零安装,SVG)或本地 Firefox CLI(PNG + SVG,可离线)
- **渲染自检循环** —— 导出 PNG 后*真的看一眼*,修掉文字截断 / 元素重叠 / 箭头穿模再交付 —— 因为光看 JSON 判断不了一张图
- **迭代评审循环** —— 渲染干净后,把结果给你看,按你的反馈做定向编辑、重新导出,直到满意(5 轮安全阀)

## 🖼️ 示例

> [!TIP]
> **页首那张图就是用下面这条提示词生成的:**

```
画一个微服务电商架构图,包含 Mobile/Web/Admin 客户端,API Gateway,
Auth/User/Order/Product/Payment 微服务,Kafka 消息队列,Notification 服务,
User DB / Order DB / Product DB / Redis Cache / Stripe API
```

除了页首那张架构图,同一个技能从简洁框线图、到**社区库里的真实图标**、再到**手绘草图**都能画 —— 全部来自自然语言,且**每张都经过真实渲染验证**:

<table>
  <tr>
    <td align="center" width="50%"><b>流程图</b><br/>椭圆起止、菱形判断、Yes/No 分支、直角折线<br/><img src="assets/flowchart-example.png" width="380" alt="流程图 —— 表单提交,Valid? 判断分流到 Save to DB 或 Show Errors"></td>
    <td align="center" width="50%"><b>时序图</b><br/>参与者、虚线生命线、实线请求 / 虚线响应<br/><img src="assets/sequence-example.png" width="380" alt="时序图 —— User / API / DB 的 login、query、rows、token 消息"></td>
  </tr>
  <tr>
    <td align="center"><b>Azure Web 应用</b> · <i>社区图标</i><br/>真实的 App Service / SQL Database / Blob Storage 图标<br/><img src="assets/azure-architecture-example.png" width="380" alt="Azure Web 应用 —— Users 经 App Service 到 SQL Database 与 Blob Storage,使用真实 Azure 图标"></td>
    <td align="center"><b>GCP 数据管道</b> · <i>社区图标</i><br/>Pub/Sub → Dataflow → BigQuery,旁挂 Cloud Storage<br/><img src="assets/gcp-pipeline-example.png" width="380" alt="GCP 数据管道 —— Events 经 Pub/Sub、Dataflow 到 BigQuery,旁挂 Cloud Storage,使用真实 GCP 图标"></td>
  </tr>
  <tr>
    <td align="center"><b>网络拓扑</b> · <i>社区图标</i><br/>Cisco 风格防火墙、路由器、交换机,扇出到主机<br/><img src="assets/network-topology-example.png" width="380" alt="办公网络 —— Internet 经防火墙、路由器、交换机到服务器、客户端、工作站,使用 Cisco 风格网络图标"></td>
    <td align="center"><b>手绘风</b> · <i>草图风格</i><br/>roughness + Virgil 字体 + 斜线填充 + emoji 图标<br/><img src="assets/hand-drawn-example.png" width="380" alt="手绘草图 —— Idea、Design、Build、Ship 方框,抖动手绘风格,带 emoji 图标"></td>
  </tr>
</table>

## 🎨 设计体系

图看起来是经过设计的、而非随机堆砌的,因为每张图都建立在一套统一的设计体系上。在排布之前,技能会先把**你描述里的关系**映射到一个可视化*隐喻* —— 隐喻比类型标签更能决定一张图的形状:

| 关系 | 可视化隐喻 | 用什么搭 |
| --- | --- | --- |
| 一对多(广播、分发) | 扇出 Fan-out | 一个节点,箭头向外辐射 |
| 多对一(聚合、汇流) | 汇聚 Convergence | 多个输入,箭头汇入一个节点 |
| 父对子(层级) | 树 Tree | 主干 + 分支线,自由文字 |
| 循环往复(回路、反馈) | 环 Cycle | 节点成环,曲线箭头回到起点 |
| 输入 → 变换 → 输出 | 流水线 Assembly line | 从左到右的步骤管道 |
| A 对 B(对比) | 并排 Side-by-side | 共享基线的两列并排 |
| 前后 / 阶段切换 | 留白 Gap | 用空白或虚线分隔分组 |
| 模糊 / 重叠状态 | 云 Cloud | 重叠椭圆,无硬边界 |

时间线 = 基准线 + 圆点,层级 = 线 + 文字 —— 结构和排版本身承载含义,方框只留给真正的组件。

<details>
<summary><b>配色、间距、箭头与字体</b> —— 点击展开</summary>

**语义配色** —— 8 类映射到含义:主要(蓝)、成功(绿)、警告(黄)、错误(红)、外部(紫)、流程(天蓝)、触发(橙)、中性(灰蓝)。遵循 **60-30-10 法则**:60% 留白、30% 主色调、10% 强调色。

**字体层次** —— 标题 28px → 组标题 24px → 标签 20px → 描述 16px → 注释 14px。

**智能尺寸** —— 按标签文字自动算宽度:西文 `max(160, charCount × 9)`,CJK `max(160, charCount × 18)` —— 标签不再被截。

**间距体系**

| 场景 | 间距 |
| ------ | ------ |
| 有标签箭头间距 | 150–200px |
| 无标签箭头间距 | 100–120px |
| 列间距(有标签) | 400px |
| 列间距(无标签) | 340px |
| 区域内边距 | 50–60px |

**箭头路由** —— 直线(默认)、L 形折线(`points` 直角转折)、曲线弯折(`roundness: { type: 2 }`)。

**箭头语义** —— 实线 = 主流程,虚线 = 响应 / 异步,点线 = 可选 / 弱依赖。

**反模式防护** —— 区域文字居中重叠、跨区域箭头面条化、短箭头标签碰撞、容器透明度规则,都写在 SKILL.md 里,让 agent 在生成前就规避。

</details>

## 🚀 安装

### 1. 选一个导出后端

| 后端 | 安装命令 | 输出 | 备注 |
|------|----------|------|------|
| **Kroki API** | `curl --version` | SVG | 零安装 —— macOS / Linux / Git Bash / WSL 默认自带 |
| **本地 CLI** | `npm install -g excalidraw-brute-export-cli && npx playwright install firefox` | PNG + SVG | PNG 必需;支持离线 |

<details>
<summary><b>macOS 本地 CLI 一次性补丁</b> —— 点击展开</summary>

CLI 按的是 `Control+O` / `Control+Shift+E`,但 macOS 需要 `Meta`(Cmd)键。装好 CLI 后执行一次即可(Windows、Linux 无需额外步骤):

```bash
CLI_MAIN=$(npm root -g)/excalidraw-brute-export-cli/src/main.js
sed -i '' 's/keyboard.press("Control+O")/keyboard.press("Meta+O")/' "$CLI_MAIN"
sed -i '' 's/keyboard.press("Control+Shift+E")/keyboard.press("Meta+Shift+E")/' "$CLI_MAIN"
```

</details>

### 2. 安装技能

```bash
# 任意 Agent(Claude Code、Cursor、Copilot 等)
npx skills add Agents365-ai/365-skills -g
```

```text
# Claude Code 插件市场
> /plugin marketplace add Agents365-ai/365-skills
> /plugin install excalidraw
```

```bash
# 手动安装
git clone https://github.com/Agents365-ai/excalidraw-skill.git \
  ~/.claude/skills/excalidraw-skill
```

同时索引于 [SkillsMP](https://skillsmp.com/skills/agents365-ai-excalidraw-skill-skills-excalidraw-skill-skill-md) 与 [ClawHub](https://clawhub.ai/agents365-ai/excalidraw-skill)。

## ⚡ 快速开始

装好之后直接描述你想要的图表,例如一张系统设计草图:

```
画一个 Python Web 应用的 CI/CD 流水线:开发者 push 到 GitHub 后触发
GitHub Actions,并行跑 lint、单元测试、安全扫描,然后构建 Docker 镜像
推送到 GHCR,通过 ArgoCD 部署到 staging,再走人工审批门发布到 production。
```

Skill 会自动选择图表模式、套用语义配色、按标签计算尺寸、规划箭头路由、写出 `.excalidraw` JSON,并导出为你指定的格式。

## 🧩 支持的图表类型

| 模式 | 示例 | 关键规则 |
| ------ | ------ | --------- |
| 架构图 | 微服务、云栈、网络拓扑、部署 | 列间距 340–400px,虚线 `Neutral` 区域透明度 25–40 |
| 流程图 | 业务流程、决策树、状态机 | 椭圆 start/end、菱形判断,"Yes" 前进 / "No" 下行 |
| 时序图 | API 调用、RPC 跟踪 | 参与者间距 200px,虚线生命线,虚线 = 响应 |
| 思维导图 | 头脑风暴、主题拆解 | 辐射布局,4 级尺寸(200→90px)按深度递减,用 line 而非 arrow |
| 泳道图 | 跨团队交接、多角色流程 | 透明虚线泳道,28px 独立泳道标签,从左到右流动 |

各模式完整的间距 / 路由规则与反模式列表见 [`SKILL.md`](skills/excalidraw-skill/SKILL.md)。

## 🧩 用社区库里的真实图标

光有方框不够?[Excalidraw 社区库](https://libraries.excalidraw.com)(200+ 个 `.excalidrawlib` —— AWS、Azure、GCP、网络拓扑、C4、BPMN、UML、电路……)本质上就是用这个 skill 所导出的**同一批矢量原语**拼的,所以它们的图标**能走 Kroki / 本地 CLI 渲染** —— 没有 `image` 元素、不需要 `files` 映射。内置脚本(`scripts/excalidraw_lib.py`)负责搜库、列 item,并把某个 item 并入你的场景(ID 命名空间化、坐标平移):

```bash
python scripts/excalidraw_lib.py search aws
python scripts/excalidraw_lib.py merge scene.excalidraw \
    slobodan/aws-serverless.excalidrawlib 0 455 257 --scale 0.9 --prefix lambda
```

<p align="center">
  <img src="assets/library-icons-example.png" width="760" alt="Serverless 请求流 —— Web/Mobile 客户端经过从 Excalidraw 社区库嵌入的真实 AWS CloudFront、Lambda、DynamoDB、S3 图标">
</p>

> 上图嵌入了从社区库直接取来的真实 AWS 图标(CloudFront、Lambda、DynamoDB、S3),并和其他图一样经过了渲染自检。

## 🔄 工作流程

<p align="center">
  <img src="assets/workflow-example.png" width="900" alt="技能流水线 —— 检测 → 规划 → 生成 → 导出 → 自检 → 回报,带一条从「自检」回到「生成」的虚线反馈回路(修正并重新导出,直到干净)。这张图本身就是用该技能画出并经渲染自检验证的。">
</p>

> 上面这张流水线图就是技能自己画的,而且走了它所记录的同一套渲染自检循环。

1. **检测依赖** —— `curl`(Kroki)或本地 `excalidraw-brute-export-cli`
2. **规划** —— 识别图表类型,选模式,挑语义配色
3. **生成** —— 写出 `.excalidraw` JSON(10+ 元素时按段拼接,seed 命名空间避免冲突)
4. **导出** —— `curl` 走 Kroki 出 SVG,或本地 CLI 出 1x–3x PNG / SVG
5. **渲染自检** —— 导出 PNG 后*真的看一眼*,修掉文字截断 / 重叠 / 箭头穿模,再重新导出(1–3 轮)
6. **评审循环** —— 把结果给你看,按你的反馈做定向编辑、重新导出,直到满意(5 轮安全阀)
7. **回报** —— 返回输出文件路径

没有 MCP server、没有后台 daemon —— 设计体系在生成前把住大头,再用一轮渲染自检(导出 PNG → 查看 → 修正)兜住 JSON 看不出来的问题。

## 🤔 为什么用 Skill 而不是 MCP?

Excalidraw 的格式就是一个元素数组,每个元素有 x/y/width/height —— Claude 天然就能写。Skill 教 Claude「怎么画」,MCP 给 Claude「一个画笔」。当模型自己就能画时,教它怎么画胜过给它工具:没有服务要起、没有运行时要装,模型还能完整掌控布局语义。

| 维度 | Skill(本技能) | MCP Server |
| ------ | ---------------- | ------------ |
| 原理 | 提示词注入到上下文 | 独立运行的服务进程 |
| 生成方式 | Claude 直接写 JSON | 需要代码处理 JSON 生成 |
| 灵活性 | 自由布局,理解语义 | API 参数固定 |
| 安装 | 复制一个文件 | 启动服务、配置 MCP |
| 依赖 | 零 | Node.js / Python 运行时 |

MCP 的价值在于提供 Claude **自身做不到的能力** —— 数据库访问、浏览器自动化、带认证的 API。图表生成的核心是 设计布局 + 写 JSON,恰恰是 LLM 最擅长的。

## 🆚 对比

### 对比原生智能体(无 skill)

| 功能 | 原生智能体 | excalidraw-skill |
| ------ | ----------- | ------------------ |
| 合法 `.excalidraw` JSON | ❌ 常常无效 / 不可交互 | ✅ 合法 schema,箭头绑定完整 |
| 语义配色 | 随机 / 不一致 | ✅ 8 类调色板 + 60-30-10 法则 |
| 字号层级 | 临场拍脑袋 | ✅ 5 级(28 / 24 / 20 / 16 / 14) |
| 图表类型预设 | ❌ | ✅ 5 种模式,各有专属间距 |
| CJK 尺寸适配 | ❌ 中文标签被截 | ✅ CJK 字符宽度翻倍 |
| 反模式防护 | ❌ | ✅ 区域重叠、面条箭头、标签碰撞均有文档 |
| 一键导出 PNG / SVG | ❌ 需手动追问 | ✅ Kroki(`curl`)或本地 CLI |
| excalidraw.com 中可编辑 | 部分 | ✅ 箭头绑定完整保留 |
| 自检 + 评审循环 | ❌ 从不看渲染结果 | ✅ 看 PNG、修缺陷,再按反馈迭代(≤5 轮) |

### 对比其他 Excalidraw skill

Excalidraw skill 赛道很挤。星标最高的两个 —— **[coleam00/excalidraw-diagram-skill](https://github.com/coleam00/excalidraw-diagram-skill)**(~3.4k★)和 **[yctimlin/mcp_excalidraw](https://github.com/yctimlin/mcp_excalidraw)**(~2k★)—— 率先做了「渲染自检循环」;本技能在 v1.2.0 也引入了它,同时保持零安装、并针对轻量导出路径做了适配。

| | **本技能** | coleam00(~3.4k★) | mcp_excalidraw(~2k★) | 多数其他 |
| --- | --- | --- | --- | --- |
| 安装负担 | **零安装** 走 Kroki(`curl`);仅 PNG 才需 Firefox CLI | `uv` + Playwright **Chromium** | Node **MCP 服务进程** | 各异 |
| 是否限于 Claude Code | ✅ 任意 [Agent Skills](https://agentskills.io) agent(Cursor、Copilot、Codex…) | Claude Code | MCP 客户端 | 多数仅 Claude Code |
| 渲染 → 查看 → 修正循环 | ✅(v1.2.0) | ✅(首创) | ✅ 实时画布 | ✗ 通常没有 |
| 静态导出适配(端到端端点、箭头标签遮罩) | ✅ 有文档且经验证 | 不涉及 —— 渲染真实 Excalidraw | 不涉及 —— 实时画布 | ✗(部分还建议中心到中心) |
| CJK 尺寸适配 + 双语触发 | ✅ | ✗ | ✗ | ✗ |
| 语义设计体系(配色、间距、字号层级) | ✅ | ✅ | 部分 | 各异 |
| 输出 | `.excalidraw` + PNG / SVG | PNG | 实时画布 + 导出 | 各异 |

**各自的强项:** coleam00 是单图生成最精致的(Chromium 渲染 = 像素级还原);mcp_excalidraw 适合实时、可交互的画布编辑。选**本技能**的理由:不想要重运行时(只需 `curl`)、用的是 **Claude Code 以外的 agent**、需要**双语 / 中文**图表,或想要在多数 skill 没适配的 **Kroki / CLI 导出路径**下也输出正确。

## 🎯 何时用(以及何时别用)

**适合:**

- 手绘 / 潦草风格的图 —— 线框图、原型、头脑风暴、非正式架构图
- 亲和、低保真的"草稿,非最终稿"观感(手绘填充、箭头、文字)
- 比起精确度,更看重亲和力与个性的可视化

**这些情况请改用同系列的其它 skill:**

- **精致、精确的图,严格 UML,或品牌厂商图标** → [drawio-skill](https://github.com/Agents365-ai/drawio-skill)
- **以代码形式存进 git、从文本自动布局的图** → [mermaid-skill](https://github.com/Agents365-ai/mermaid-skill)(通用)或 [plantuml-skill](https://github.com/Agents365-ai/plantuml-skill)(UML)
- **无限画布白板或程序化自由笔迹** → [tldraw-skill](https://github.com/Agents365-ai/tldraw-skill)

## 🔗 相关 Skill

[Agents365-ai 图表 skill 家族](https://github.com/Agents365-ai) 一员 —— 按场景挑工具:

| Skill | 风格 | 适用场景 |
| --- | --- | --- |
| [drawio-skill](https://github.com/Agents365-ai/drawio-skill) | 精修、汇报级 | 架构图、UML、ML/DL 图、正式文档 |
| [mermaid-skill](https://github.com/Agents365-ai/mermaid-skill) | 文本驱动、自动布局 | 可嵌入 README、易于版本管理 |
| [plantuml-skill](https://github.com/Agents365-ai/plantuml-skill) | UML 专精 | CI 流水线里的类图 / 序列图 |
| [tldraw-skill](https://github.com/Agents365-ai/tldraw-skill) | 白板协作 | 随手画、FigJam 风格 |

## ❤️ 支持作者

如果这个 skill 对你有帮助,欢迎支持作者:

<table>
  <tr>
    <td align="center">
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/qrcode/wechat-pay.png" width="180" alt="微信支付">
      <br>
      <b>微信支付</b>
    </td>
    <td align="center">
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/qrcode/alipay.png" width="180" alt="支付宝">
      <br>
      <b>支付宝</b>
    </td>
    <td align="center">
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/qrcode/buymeacoffee.png" width="180" alt="Buy Me a Coffee">
      <br>
      <b>Buy Me a Coffee</b>
    </td>
    <td align="center">
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/awarding/award.gif" width="180" alt="打赏">
      <br>
      <b>打赏</b>
    </td>
  </tr>
</table>

## 👤 作者

**Agents365-ai**

- GitHub: <https://github.com/Agents365-ai>
- Bilibili: <https://space.bilibili.com/441831884>

## 📄 许可证

[MIT](LICENSE)
