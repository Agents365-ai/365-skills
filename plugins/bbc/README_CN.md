# bbc-skill · 哔哩哔哩评论采集

[English README](README.md)

> UP 主专属：一键拉取自己视频的全部评论，交给 Claude Code / Codex / Gemini / 任何 agent 做情感 / 关键词 / 受众分析。

- 🐍 **零依赖** — 只用 Python 3.9+ 标准库，不需要 `pip install`
- 💬 **完整评论** — 顶级评论 + 楼中楼 + 置顶评论，一条不落
- 📊 **视频元数据** — 标题、播放、点赞、投币、收藏、标签一起拉
- 🤖 **Agent-native CLI** — stdout 稳定 JSON envelope，stderr NDJSON 进度，exit code 分类、dry-run、schema 自描述
- 🧑‍🎤 **批量模式** — 一个命令拉 UP 主全部视频评论，串行处理（一个视频一个视频来，视频之间随机休眠 5-10s）
- 🔐 **认证委托** — 人登录 / agent 使用；纯 cookie 文件，不做浏览器自动化
- ♻️ **断点续传** — 重跑同一 BV 自动跳过已拉页；`--since` 支持增量
- 📁 **分析友好输出** — `comments.jsonl` + `summary.json` + `raw/` 归档

## ⚠️ 合理使用声明

**请阅读并遵守以下准则，否则请不要使用本工具。**

- ✅ **仅限个人、少量、合法使用**：分析**你自己**视频的评论，或获得 UP 主明确授权后协助分析。
- ✅ **保持节制**：批量模式已内置 5-10s 随机间隔和 1s 每请求节流；请不要修改源码绕过这些限制。
- ❌ **禁止滥用场景**：
  - 大规模爬取陌生 UP 的视频评论
  - 构建二级数据产品对外出售 / 公开发布
  - 绕过速率限制、伪造 User-Agent、使用代理池规避风控
  - 高频自动化任务（每日多次全量扫描同一 UP 主的所有视频）
  - 把采集到的数据用于骚扰、网络暴力、人肉、定向引战
- 📜 **遵守 B 站用户协议** 与 [robots](https://www.bilibili.com/robots.txt)；商业场景请走 [B 站开放平台](https://openhome.bilibili.com/) 官方 API。
- 🔒 **数据最小化原则**：拉完就分析；不要无限期留存、也不要把含用户个人信息（UID、IP 属地）的 raw 数据分享出去。
- 🎯 **读完即删的工作流更健康**：本工具设计就是为了「一次分析一批视频」，不是为了搞长期监控。

> 本项目作者与 bilibili.com 无任何关联。使用本工具造成的任何账号风控、封禁、法律后果由使用者自行承担。如果你不确定某个使用场景是否合规，**请不要跑**。

---

## 安装

这是一个纯自包含的常规 skill:只用 Python 3.9+ 标准库，零 `pip install`。
skill 位于 Agents365-ai 的 skills monorepo；clone 整个 monorepo，再把 skill 目录
链接或复制到 agent 的 skills 路径：

```bash
# 全局（以 Claude Code 为例；其他 agent 用各自的 skills 路径）
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/bbc/skills/bbc-skill" ~/.claude/skills/bbc-skill

# 项目级
ln -s "$(pwd)/365-skills/plugins/bbc/skills/bbc-skill" .claude/skills/bbc-skill
```

不走 skill 运行时、直接命令行用也可以：

```bash
git clone https://github.com/Agents365-ai/365-skills.git
cd 365-skills/plugins/bbc/skills/bbc-skill
python3 -m bbc --help
```

---

## 一分钟上手

### 第 1 步 · 导出 B 站 cookie

> **为什么要 cookie**：B 站评论 API 对未登录请求会限速且缺字段。UP 主做自己视频分析需要完整数据，所以必须带 cookie。

**推荐方式**：Chrome 插件 [**Get cookies.txt LOCALLY**](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)（开源、完全本地、不上传任何数据）。

1. Chrome 商店安装 **Get cookies.txt LOCALLY**
2. 打开 [https://www.bilibili.com](https://www.bilibili.com)，**确认自己已登录**（右上角有头像）
3. 点插件图标 → **Export** → 下载 `www.bilibili.com_cookies.txt`
4. 把文件放到你方便的位置，例如 `~/Downloads/bilibili_cookies.txt`

**其他导出方式**：

- Firefox：安装 [cookies.txt](https://addons.mozilla.org/firefox/addon/cookies-txt/) 插件，操作类似
- Edge：同 Chrome 插件（Edge 兼容 Chrome 扩展）
- 命令行手动：浏览器 F12 → Application → Cookies → 复制 `SESSDATA` 值，然后 `export BBC_SESSDATA="值"`

**不要**分享 `SESSDATA` —— 泄露等于账号被盗。

### 第 2 步 · 验证 cookie 能用

```bash
./scripts/bbc cookie-check --cookie-file ~/Downloads/bilibili_cookies.txt
```

期望输出：

```json
{"ok": true, "data": {"mid": 441831884, "uname": "探索未至之境", "vip": true, "level": 5, ...}}
```

失败？检查：

- 确认 bilibili.com **当前已登录**（cookie 导出时处于登录态）
- `SESSDATA` 不要手动改动
- 两周未登录可能过期，重新登录一次再导出

### 第 3 步 · 拉你的视频评论

```bash
./scripts/bbc fetch BV1NjA7zjEAU \
  --cookie-file ~/Downloads/bilibili_cookies.txt
```

也可以直接传 URL：

```bash
./scripts/bbc fetch "https://www.bilibili.com/video/BV1NjA7zjEAU/"
```

输出在 `./bilibili-comments/BV1NjA7zjEAU/`：

```
bilibili-comments/BV1NjA7zjEAU/
├── comments.jsonl      # 主数据，每行一条评论
├── summary.json        # 视频元数据 + 统计 + Top-N
├── raw/                # 原始 API 响应归档
└── .bbc-state.json     # 断点 & 增量标记
```

---

## 环境变量（免反复传参）

```bash
export BBC_COOKIE_FILE="$HOME/Downloads/bilibili_cookies.txt"
./scripts/bbc fetch BV1NjA7zjEAU      # 自动读取
```

或者直接传 SESSDATA：

```bash
export BBC_SESSDATA="从 F12 复制的值"
./scripts/bbc fetch BV1NjA7zjEAU
```

---

## 给 Claude Code 用的分析工作流

拉完之后告诉 Claude：

> 读取 `./bilibili-comments/BV1NjA7zjEAU/summary.json`，先给我看整体情况：视频基础数据、评论分布、Top 20 热评。然后我会告诉你接下来分析什么。

Claude 会按这个路径做：

1. **先读 `summary.json`**（几 KB）建立全局认知：视频标题、播放量、评论数、时间分布、IP 分布、Top-N 热评 / 回复数
2. **按需采样 `comments.jsonl`** —— 每行一条 JSON，可以 `Grep` 关键词、`head`/`tail` 看最新最早、按 `like` 排序取头部
3. **典型分析方向**：
   - **情感倾向**：正面 / 负面 / 中性占比
   - **高频词**：除了停用词以外的主题词
   - **UP 主互动**：`is_up_reply=true` 的评论，看你回了哪些、哪些漏回
   - **地域分布**：`ip_location` 直方图
   - **反馈演变**：按 `ctime_iso` 分周 / 月，看发布后一周 vs 长尾
   - **铁粉识别**：按 `mid` 聚合，同一用户评论多次的名单
   - **差评筛查**：`like` 高且含 "垃圾/太水/不行" 类词的评论

---

## 命令参考

### `bbc fetch <BV|URL>`

```
--max N                每个视频顶级评论上限（默认全拉）
--since <日期>         只拉这个时间后的新评论（ISO 格式，如 2026-04-01）
--output <dir>         输出目录（默认 ./bilibili-comments/<BV>/）
--cookie-file <path>   cookie 文件路径
--browser <name>       auto / firefox / chrome / edge / safari
--format json|table    stdout 格式
--dry-run              预览请求计划，不发网络
--force                忽略断点，重头抓
```

### `bbc fetch-user <UID>`

批量拉 UP 主所有视频的评论，串行处理，视频之间随机休眠 5-10s。

```bash
python3 -m bbc fetch-user 441831884 --cookie-file cookies.txt
python3 -m bbc fetch-user 441831884 --video-limit 2   # 先小批量试跑
```

### `bbc summarize <dir>`

从已有 `comments.jsonl` 重建 `summary.json`（当你手动修改了原始数据时有用）。

### `bbc cookie-check`

验证 cookie 可用性，打印登录用户信息。

### `bbc schema [command]`

返回命令的 JSON schema（参数类型、exit code 映射、错误码）。供 agent 自描述用。

### Exit codes

| 码 | 含义 |
| --- | --- |
| 0 | 成功 |
| 1 | 运行时 / B站 API 错误 |
| 2 | 认证错误（cookie 无效 / 过期） |
| 3 | 参数校验错误（BV 格式错等） |
| 4 | 网络错误（超时、重试耗尽） |

---

## 输出格式说明

### `comments.jsonl` 单条记录

```json
{
  "rpid": 296636680849,
  "bvid": "BV1NjA7zjEAU",
  "parent": 0,
  "root": 0,
  "mid": 71171081,
  "uname": "蓝忘今宵-_-YS",
  "user_level": 4,
  "vip": false,
  "ctime": 1776521119,
  "ctime_iso": "2026-04-18T06:25:19+00:00",
  "message": "已关注 求指教",
  "like": 1,
  "rcount": 0,
  "ip_location": "河北",
  "is_up_reply": false,
  "top_type": 0,
  "mentioned_users": [],
  "jump_urls": []
}
```

- `parent=0` → 顶级评论；否则指向父评论 rpid
- `top_type`：0=普通, 1=UP 置顶, 2=热评置顶
- `is_up_reply`：是否是 UP 主本人回复

### `summary.json` 字段一览

- `video`：标题、简介、播放量、点赞、投币、收藏、标签、封面 URL、UP 主
- `counts`：总数、顶级数、楼中楼数、置顶数、唯一用户数、UP 回复数、完整度
- `time_distribution`：最早 / 最晚评论时间、按天分布
- `top_liked`：Top N 点赞评论
- `top_replied`：Top N 被回复评论
- `ip_distribution`：IP 属地分布

详细 schema 见 `references/agent-contract.md`。

---

## 限制 & 注意事项

- **只读** — 本工具不发布 / 修改 / 删除任何评论，安全分层为 `open`
- **速率** — 每请求间隔 1s（顶级）/ 0.5s（楼中楼），5000 条约 10-15 分钟
- **反风控** — 连续多次抓取可能触发 HTTP 412，已内建指数退避重试 3 次
- **完整度** — summary 中 `completeness` 显示实拉 / 接口声称总数；<1.0 说明有被删评论或接口不一致
- **不支持匿名** — UP 主分析必须带 cookie；未登录请求返回字段不完整

---

## 相关文档

- [SKILL.md](./SKILL.md) — 给 Claude 的触发 & 使用指引
- [references/api-endpoints.md](./references/api-endpoints.md) — 所用 B 站接口字段
- [references/agent-contract.md](./references/agent-contract.md) — envelope / exit code / schema 契约

---

## 贡献

欢迎提 issue、PR、建议。无论是新的分析场景、更稳的反风控默认值、其他平台支持、文档改进 —— 任何贡献都欢迎。[提 Issue](https://github.com/Agents365-ai/365-skills/issues) 或直接发 PR。

---

## Support

如果这个 skill 帮到了你，可以请作者喝杯咖啡 ☕

<table>
  <tr>
    <td align="center">
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/qrcode/wechat-pay.png" width="180" alt="微信支付">
      <br>
      <b>WeChat Pay</b>
    </td>
    <td align="center">
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/qrcode/alipay.png" width="180" alt="支付宝">
      <br>
      <b>Alipay</b>
    </td>
    <td align="center">
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/qrcode/buymeacoffee.png" width="180" alt="Buy Me a Coffee">
      <br>
      <b>Buy Me a Coffee</b>
    </td>
  </tr>
</table>

---

## 作者

**Agents365-ai** &mdash; 为 AI coding agent 制作开源 skill。

- B 站：<https://space.bilibili.com/441831884>
- GitHub：<https://github.com/Agents365-ai>

---

## License

MIT
