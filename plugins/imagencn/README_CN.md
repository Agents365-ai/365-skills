# imagencn — 阿里云百炼 AI 图像生成技能

[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-skill-6C3C97)](https://claude.ai/code)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-compatible-orange)](https://openclaw.ai)
[![SkillsMP](https://img.shields.io/badge/SkillsMP-indexed-blue)](https://skillsmp.com)

[English](README.md)

**imagencn — Image Generation, Cloud-Native：一个 CLI，接入所有图像生成云端。** 项目从中国友好的云平台起步，现已覆盖国际平台。

自然语言生成高质量图像的 Claude Code / OpenClaw 技能，支持阿里云百炼、字节火山方舟、腾讯混元、智谱 BigModel、阶跃星辰以及 Google Gemini、Grok（xAI）、OpenAI、Black Forest Labs（FLUX）九大平台。

📋 **[模型参考](https://agents365-ai.github.io/imagenCN/docs/models.html)** — 浏览全部 44 个模型，含价格、分辨率、功能对比。

## 工作流程

<img src="assets/workflow-cn.png" width="450" alt="imagencn 工作流程">

## 特性

- **阿里云百炼 (DashScope)**: 通义千问 2.0、编辑版、万相系列、Z-Image — 共 21 个模型
- **字节火山方舟**: 豆包 Seedream 系列 (5.0/4.5/4.0) — 3 个模型，最高 4K
- **腾讯混元**: 混元生图 3.0 — 旗舰模型，复杂中文语义理解
- **智谱 / BigModel**: CogView-4、GLM-Image — 3 个模型，图片中直接渲染中文文字
- **阶跃星辰**: Step-2X、Step-Image-Edit-2 — 2 个模型，超低价批量生成
- **Google Gemini**（国际平台）: Gemini 3 Pro Image / 3.1 Flash Image — 4 个模型，512/1K/2K/4K 及比例预设
- **Grok / xAI**（国际平台）: Grok Imagine — 3 个模型，比例 + 分辨率预设，最高 4K
- **OpenAI**（国际平台）: GPT Image 1/1.5/2 — 4 个模型，任意尺寸最高 4K（gpt-image-2）
- **Black Forest Labs / FLUX**（国际平台）: FLUX.2 Pro / Max — 3 个模型，异步 API，灵活比例 + 种子控制
- **多种尺寸预设**: 1:1, 16:9, 9:16, 4:3, 3:4，以及 1K/2K/3K/4K
- **跨平台**: 支持 Windows, macOS, Linux
- **多区域 API**: 中国（默认）、新加坡、弗吉尼亚（DashScope）

## 安装

### Claude Code 插件市场（推荐）

```bash
/plugin install imagencn@365-skills
```

或者告诉你的 coding agent：
> help me to install <https://github.com/Agents365-ai/365-skills>

### 手动安装

skill 位于 Agents365-ai 的 skills monorepo；clone 整个 monorepo，再把 skill 目录
链接或复制到 agent 的 skills 路径：

```bash
git clone https://github.com/Agents365-ai/365-skills.git

# 全局安装（以 Claude Code 为例；其他 agent 用各自的 skills 路径）
ln -s "$(pwd)/365-skills/plugins/imagencn/skills/imagencn" ~/.claude/skills/imagencn

# 仅当前项目
ln -s "$(pwd)/365-skills/plugins/imagencn/skills/imagencn" .claude/skills/imagencn
```

### OpenClaw

```bash
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/imagencn/skills/imagencn" skills/imagencn
```

### SkillsMP

在 [skillsmp.com](https://skillsmp.com) 搜索 `imagencn`，一键安装。

## 系统要求

### 环境要求

- Python 3.8+
- pip

### 安装依赖

```bash
pip install dashscope requests
```

### API 密钥

```bash
# 阿里云百炼 (DashScope)
export DASHSCOPE_API_KEY="your_api_key"
# 获取密钥: https://bailian.console.aliyun.com/

# 字节火山方舟（可选）
export ARK_API_KEY="your_api_key"
# 获取密钥: https://console.volcengine.com/ark/region:ark+cn-beijing/apikey

# 腾讯混元（可选）
export HUNYUAN_API_KEY="your_api_key"
# 获取密钥: https://console.cloud.tencent.com/tokenhub/apikey

# 智谱 / BigModel（可选）
export ZHIPUAI_API_KEY="your_api_key"
# 获取密钥: https://bigmodel.cn

# 阶跃星辰（可选）
export STEP_API_KEY="your_api_key"
# 获取密钥: https://platform.stepfun.com/interface-key

# Google Gemini（可选，国际平台）
export GEMINI_API_KEY="your_api_key"
# 获取密钥: https://aistudio.google.com/

# Grok / xAI（可选，国际平台）
export XAI_API_KEY="your_api_key"
# 获取密钥: https://console.x.ai/

# OpenAI（可选，国际平台）
export OPENAI_API_KEY="your_api_key"
# 获取密钥: https://platform.openai.com/api-keys
```

### 配置文件（可选）

创建 `~/.imagencn.json` 设置个人默认值：

```json
{"platform": "ark", "model": "doubao-seedream-5-0-260128", "size": "2K"}
```

项目级 `.imagencn.json` 优先级高于用户级。命令行参数覆盖两者。

> **从 imagenCN（≤1.1.x）升级？** skill 已改名为小写 `imagencn`，配置文件也请一并重命名：`mv ~/.imagenCN.json ~/.imagencn.json`（安装目录 `~/.claude/skills/imagenCN` → `~/.claude/skills/imagencn`）。

### 可选环境变量

```bash
# 各平台默认模型
export DASHSCOPE_MODEL="wan2.7-image-pro"       # DashScope 默认
export ARK_MODEL="doubao-seedream-5-0-260128"   # 火山方舟默认
export HUNYUAN_MODEL="hy-image-v3.0"            # 腾讯混元默认
export ZHIPUAI_MODEL="cogview-4"                # 智谱默认
export STEP_MODEL="step-2x-large"               # 阶跃星辰默认
export GEMINI_MODEL="gemini-3-pro-image-preview" # Google Gemini 默认
export XAI_MODEL="grok-imagine-image-quality"    # Grok / xAI 默认
export OPENAI_MODEL="gpt-image-1"                # OpenAI 默认
export BFL_MODEL="flux-2-pro-preview"            # FLUX 默认

# 设置 API 端点（仅 DashScope，默认: cn）
export DASHSCOPE_API_BASE="cn"  # 或 "sg", "us", 或完整 URL
```

## 快速开始

### 自然语言（Claude Code）

直接告诉 Claude 你想要什么：

```
生成一只可爱的橘猫图片
创建一张带有"新年快乐"文字的海报
用 wan2.7-image-pro 生成一张 4K 的山间日落照片
生成一张 16:9 的风景壁纸
```

### 命令行

```bash
# 基本用法（默认模型: qwen-image-2.0-pro，原生 2K）
python scripts/generate_image.py "一只可爱的猫咪" output.png

# 使用 Wan2.7 模型生成 4K 写实图像 (DashScope)
python scripts/generate_image.py --model wan2.7-image-pro --size 4K "山间日落" photo.png

# 火山方舟（字节跳动）— 需 ARK_API_KEY
python scripts/generate_image.py --platform ark "时尚杂志封面风格人像" portrait.png

# 腾讯混元 — 需 HUNYUAN_API_KEY
python scripts/generate_image.py --platform hunyuan "月球上骑马的宇航员，电影级光影" scifi.png

# Google Gemini（国际平台）— 需 GEMINI_API_KEY
python scripts/generate_image.py --platform gemini "清晨柔光下的日式庭院" garden.png

# Grok / xAI（国际平台）— 需 XAI_API_KEY
python scripts/generate_image.py --platform grok --size 16:9 "霓虹倒影的赛博朋克城市夜景" city.png

# OpenAI（国际平台）— 需 OPENAI_API_KEY
python scripts/generate_image.py --platform openai --quality high "极简陶瓷茶壶产品图，柔和影棚光" teapot.png

# Black Forest Labs / FLUX（国际平台）— 需 BFL_API_KEY
python scripts/generate_image.py --platform bfl --size 16:9 "黄昏时分的火山海岸线" coast.png

# 编辑已有图片（需 --image）
python scripts/generate_image.py --model qwen-image-edit-max --image input.png "把背景换成海滩日落" edited.png

# 使用负面提示词
python scripts/generate_image.py --negative "模糊" "高质量人像" portrait.png

# 列出九大平台全部模型
python scripts/generate_image.py --list-models
```

## 模型

| 模型 | 最佳用途 |
| ------ | ---------- |
| `qwen-image-2.0-pro` | **默认**，最新旗舰，原生 2K，最强字体与细节 |
| `qwen-image-2.0-pro-2026-06-22` | 最新快照版（2026 年 6 月），生成与编辑能力融合 |
| `qwen-image-2.0` | 标准 2.0 版本，原生 2K |
| `qwen-image-max` | 上代旗舰 |
| `qwen-image-max-2025-12-30` | qwen-image-max 快照版，写实感增强、AI 痕迹更少 |
| `qwen-image-plus` | 蒸馏加速版 |
| `qwen-image-plus-2026-01-09` | qwen-image-plus 快照版（2026 年 1 月） |
| `qwen-image-edit-max` | 旗舰图像编辑模型（需 `--image`） |
| `qwen-image-edit-max-2026-01-16` | 最新编辑快照版（2026 年 1 月） |
| `qwen-image-edit-plus` | 快速低成本图像编辑 |
| `qwen-image` | 基础版 |
| `wan2.7-image-pro` | 最新写实模型，最高 4K 输出 |
| `wan2.7-image` | Wan 2.7 标准版，最高 2K |
| `wan2.6-t2i` | Wan 2.6，灵活尺寸 |
| `wan2.5-t2i-preview` | 高质量艺术作品 |
| `wan2.2-t2i-flash` | 快速生成 |
| `wan2.2-t2i-plus` | 专业级 |
| `wanx2.1-t2i-turbo` | 快速执行 |
| `wanx2.1-t2i-plus` | 专业级 |
| `wanx2.0-t2i-turbo` | 早期版本 |
| `z-image-turbo` | 轻量快速、低成本；人像和商品图 |
| `doubao-seedream-5-0-260128` | 字节最新旗舰，最高 3K，PNG/JPEG，最强文字渲染 |
| `doubao-seedream-4-5-251128` | 字节 Seedream 4.5，最高 4K |
| `doubao-seedream-4-0-250828` | 字节 Seedream 4.0，高性价比 4K |
| `hy-image-v3.0` | 腾讯混元旗舰，复杂中文语义理解，最高支持千字级 prompt |
| `cogview-4` | 智谱 CogView-4，图片中直接渲染中文文字 |
| `cogview-4-250304` | CogView-4 固定快照版（2025年3月），可复现结果 |
| `glm-image` | 智谱 GLM-Image 旗舰，最高 2048×2048 |
| `step-2x-large` | 阶跃星辰 Step-2X 高品质，0.1 元/张 |
| `step-image-edit-2` | 阶跃星辰超低价，0.02 元/张，支持负面提示词 |
| `gemini-3-pro-image-preview` | Google Gemini 旗舰（国际平台），支持 512/1K/2K 及比例预设 |
| `gemini-3-pro-image` | Google Gemini 稳定版旗舰，支持 1K/2K/4K |
| `gemini-3.1-flash-image` | Google Gemini 快速通用模型（Nano Banana 2），512/1K/2K/4K |
| `gemini-3.1-flash-lite-image` | Google Gemini 最快最便宜，仅 1K |
| `grok-imagine-image-quality` | Grok 高质量生图模型，最高 4K |
| `grok-imagine-image` | Grok 标准生图模型 |
| `grok-2-image` | Grok 旧版 JPG 模型 |
| `gpt-image-1` | OpenAI GPT Image 1，1024/1536 尺寸 |
| `gpt-image-1-mini` | OpenAI GPT Image 1 Mini，快速低价 |
| `gpt-image-1.5` | OpenAI GPT Image 1.5，质量提升 |
| `gpt-image-2` | OpenAI 旗舰，任意尺寸最高 4K |
| `flux-2-pro-preview` | FLUX.2 Pro 最新滚动版（国际平台），异步 API，内置提示词增强 |
| `flux-2-pro` | FLUX.2 Pro 固定快照版，结果可复现 |
| `flux-2-max` | FLUX.2 最高质量版，支持联网检索 |

## 尺寸预设

**通义千问 2.0（原生 2K）:**

- `1:1` → 2048×2048（默认）
- `16:9` → 2688×1536
- `9:16` → 1536×2688
- `4:3` → 2304×1728
- `3:4` → 1728×2304
- `1K` → 1024×1024
- `2K` → 2048×2048

**通义千问经典版:**

- `1:1` → 1328×1328
- `16:9` → 1664×928
- `9:16` → 928×1664
- `4:3` → 1472×1104
- `3:4` → 1104×1472

**Z-Image（像素面积 512×512 至 2048×2048）:**

- `1:1` → 1024×1024（默认）
- `16:9` → 1280×720
- `9:16` → 720×1280
- `2:3` → 1024×1536
- `3:2` → 1536×1024

**通义万相（Wan2.7 还支持 `1K`/`2K`/`4K`）:**

- `1:1` → 1024×1024
- `1:1-large` → 1280×1280
- `16:9` → 1280×720
- `9:16` → 720×1280
- `4:3` → 1200×900
- `3:4` → 900×1200
- `2:1` → 1440×720

**火山方舟 (Seedream):**

- `1:1` → 2048×2048
- `16:9` → 2848×1600
- `9:16` → 1600×2848
- `4:3` → 2304×1728
- `3:4` → 1728×2304
- `1K` / `2K` / `3K` / `4K`（取决于模型）

**腾讯混元（冒号分隔格式）:**

- `1:1` → 1024:1024
- `16:9` → 1920:1080
- `9:16` → 1080:1920
- `4:3` → 1600:1200
- `3:4` → 1200:1600
- `3:2` → 1920:1280
- `2:3` → 1280:1920

**智谱 (CogView-4 / GLM-Image):**

- `1:1` → 1024x1024（默认）
- `16:9` → 1344x768
- `9:16` → 768x1344
- `4:3` → 1152x864
- `3:4` → 864x1152
- `2:1` → 1440x720
- `1:2` → 720x1440

**阶跃星辰 (Step-2X):**

- `1:1` → 1024x1024（默认）
- `1:1-small` → 512x512
- `16:9` → 1280x800
- `9:16` → 800x1280

**Google Gemini（命名尺寸 + 宽高比）:**

- `512` / `1K`（默认）/ `2K` / `4K` → 命名输出尺寸（4K 仅 Pro / 3.1 Flash；Lite 仅 1K）
- `1:1`, `16:9`, `9:16`, `4:3`, `3:4` → 宽高比（不支持精确像素尺寸）

**Grok / xAI（宽高比 + 分辨率）:**

- `1:1`, `16:9`, `9:16`, `4:3`, `3:4`, `2:1` → 作为 `aspect_ratio` 发送（默认 1:1）
- `1K` / `2K` / `4K` → 作为 `resolution` 发送

**OpenAI (GPT Image):**

- `1:1` → 1024x1024（默认）
- `16:9` → 1536x1024，`9:16` → 1024x1536
- `4:3` → 1344x1024，`3:4` → 1024x1344
- `1K` → 1024x1024，`2K` → 2048x2048（仅 gpt-image-2），`4K` → 3840x2160（仅 gpt-image-2）

**FLUX (Black Forest Labs):**

- `1:1` → 1024x1024（默认）
- `16:9` → 1344x768，`9:16` → 768x1344
- `4:3` → 1152x864，`3:4` → 864x1152
- `2:1` → 1440x720，`1:2` → 720x1440
- `1K` → 1024x1024，`2K` → 2048x2048（也支持任意 WxH 尺寸）

## API 端点

| 地区 | 别名 | URL |
| ------ | ------ | ----- |
| **中国**（默认） | `cn` | `https://dashscope.aliyuncs.com/api/v1` |
| 新加坡 | `sg` | `https://dashscope-intl.aliyuncs.com/api/v1` |
| 弗吉尼亚 | `us` | `https://dashscope-us.aliyuncs.com/api/v1` |

## 支持

如果这个项目对你有帮助，欢迎支持作者：

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
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/awarding/award.gif" width="180" alt="打赏作者">
      <br>
      <b>打赏作者</b>
    </td>
  </tr>
</table>

## 作者

**Agents365-ai**

- Bilibili: <https://space.bilibili.com/441831884>
- GitHub: <https://github.com/Agents365-ai>

## 许可证

[CC BY-NC 4.0](LICENSE) — 非商业用途免费。商业使用需获得授权。
