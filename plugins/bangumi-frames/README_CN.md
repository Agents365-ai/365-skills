# bangumi-frames — B站番剧帧 / 角色整理

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/Agents365-ai/365-skills?style=flat&logo=github)](https://github.com/Agents365-ai/365-skills/stargazers)
[![Last Commit](https://img.shields.io/github/last-commit/Agents365-ai/365-skills?logo=github)](https://github.com/Agents365-ai/365-skills/commits/main)
[![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-plugin-8a2be2)](https://github.com/Agents365-ai/365-skills)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-2ea44f)](https://agentskills.io)
[English](README.md) · **中文**

把一个 **B站视频**(番剧 `ep`、UP主投稿 `BV`,或一个**本地视频文件**)整理成
**按角色分组的图片** 和 **风景空镜**。它下载视频、抽场景切换关键帧、用动漫专用人物检测把
帧分成风景与人物裁片,然后用 CCIP 角色身份嵌入,要么**把所有人聚类**,要么**只把某一个
指定角色全捞出来**。兼容 **Claude Code** 及任何支持 [Agent Skills](https://agentskills.io) 格式的 agent。

> 只读下载,仅供个人离线观看/分析,不上传任何东西。仅适用动漫 / 2.5D 渲染画风(真人无效)。

## 能做什么

- 输入**一条 B站视频链接**(或一个本地视频文件),自动挑出里面最精彩的画面。
- **认出画面里的动漫人物**,和风景空镜分开放。
- **全部分组** —— 自动把所有角色分好组,一个角色一个文件夹。
- **只挑指定角色** —— 给它某个角色的样图,它就把全片里这个角色出现的画面全部捞出来。参考目录里放
  多个「按角色分的子文件夹」,就能一次捞出好几个角色,各自进各自的文件夹。
- 想要干净的图,还能**先去掉硬字幕和角标水印**。

## 📦 安装

```bash
# 必需
brew install ffmpeg
pip install yt-dlp dghs-imgutils

# 可选,仅 --clean 去字幕/水印需要
pip install rapidocr-onnxruntime simple-lama-inpainting
```

首次运行从 HuggingFace 拉 ~300MB 动漫检测 + CCIP 模型(之后走缓存)。下载非预览 / 1080p+ 需要
B站 cookie(`cookies.txt`),解析顺序:`--cookies` > `$BILIBILI_COOKIES` >
`~/bb_up/bb_cookies/www.bilibili.com_cookies.txt`。

> **CCIP 阶段必须走 CPU** —— 不要设 `ONNX_MODE=CoreML`(CCIP 在 CoreML 下会崩;脚本在聚类/匹配前
> 已自动复位该变量)。人物检测在 CoreML 下没问题。

## 🚀 用法

```bash
SKILL=skills/bangumi-frames/scripts/bangumi_frames.py

# 模式1 —— 把所有人聚类成 char_NN 组
python3 $SKILL https://www.bilibili.com/video/BV15qVm68E2h --out ~/frames
python3 $SKILL ep1231575 --out ~/frames            # 也接受 ep / BV 号
python3 $SKILL ~/local.mp4 --out ~/frames           # 本地文件,跳过下载

# 模式2 —— 只捞某一个角色(参考夹放该角色 ~200 张裁片)
python3 $SKILL BV15qVm68E2h --ref ~/refs/紫灵 --ref-eps 0.04 --out ~/frames

# 模式2 —— 一次捞多个角色(参考夹里放「按角色分的子文件夹」)
#   ~/refs/凡人/{韩立,紫灵,南宫婉}/*.jpg  ->  matched/{韩立,紫灵,南宫婉}/
python3 $SKILL BV15qVm68E2h --ref ~/refs/凡人 --ref-eps 0.04 --out ~/frames

# 可选:分析前先去硬字幕和水印
python3 $SKILL ep1231575 --clean --out ~/frames
```

## 🗂️ 输出

```
<out>/<id>/                     # id = BV号 / ep号 / 本地文件名
├── frames/  frames.json        # 关键帧 + 时间戳
├── scenery/                    # 未检测到人物的帧
├── crops/  features.npy        # 人物裁片 + CCIP 特征缓存
├── detect.json                 # 帧 -> 人物框 / 裁片
├── characters/                 # 模式1:char_NN_crop/ + char_NN_full/(配对)、_unsorted/、_montage.png
├── matched/                    # 模式2:0.012_<crop>.jpg(距离前缀)+ index.json
│                               #   (多角色:每个子文件夹 -> matched/<名字>/)
├── matched_montage.png         # 模式2 抽样拼图(单角色)
└── index.json                  # 模式1:角色组 -> {crop, frame, time}
```

先看 `characters/_montage.png`(模式1)或 `matched_montage.png`(模式2)判断质量,再读 `index.json`。

## ⚙️ 原理

`input → download → extract →(clean)→ classify → cluster | match`

每阶段幂等(产物存在就跳过);聚类/匹配每次都基于缓存特征重跑。完整参数、CPU/CoreML 规则、阈值
经验都在 skill 的参考文档里:

- [`skills/bangumi-frames/references/pipeline.md`](skills/bangumi-frames/references/pipeline.md) —— 各阶段、参数、`--clean`、缓存、`--redo`
- [`skills/bangumi-frames/references/modes.md`](skills/bangumi-frames/references/modes.md) —— 模式1 vs 模式2、阈值、距离分布

## 📁 目录结构

```
skills/bangumi-frames/      # skill 本体(SKILL.md + scripts/ + references/)
```

本 skill 属于 [Agents365-ai/365-skills](https://github.com/Agents365-ai/365-skills) skills monorepo;
回归测试和 CI workflow 在独立仓库历史里,不随 plugin 提供。

## 📝 许可

[MIT](LICENSE) © Agents365-ai
