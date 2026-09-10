# bbc-skill · Bilibili Comment Collector

[中文文档](README_CN.md)

> Built for Bilibili UP主 (content creators): fetch every comment on your own
> videos and feed them to Claude Code / Codex / Gemini / any agent for
> sentiment / keyword / audience analysis.

- 🐍 **Zero dependencies** — Python 3.9+ standard library only, no `pip install`
- 💬 **Complete** — top-level + nested + pinned comments, nothing skipped
- 📊 **Video metadata** — title, view/like/coin/favorite counts, tags included
- 🤖 **Agent-native CLI** — stable stdout JSON envelope, NDJSON stderr
  progress, distinct exit codes, dry-run, schema introspection
- 🧑‍🎤 **Batch mode** — fetch every video of a UP主 sequentially (one at a time,
  5-10s randomised cooldown between videos)
- 🔐 **Delegated auth** — human logs in once, agent just consumes the cookie;
  no browser automation
- ♻️ **Resumable** — re-running the same BV skips completed pages; `--since`
  for incremental monitoring
- 📁 **Analysis-friendly** — `comments.jsonl` + `summary.json` + `raw/` archive

## ⚠️ Responsible Use

**Please read and accept these guidelines before using this tool.**

- ✅ **Personal, low-volume, legal use only**: analyze comments on **your own**
  videos, or assist another creator with their explicit authorization.
- ✅ **Respect the built-in throttling**: 1s per request, 5-10s random
  cooldown between videos in batch mode. Do not patch these out.
- ❌ **Do NOT use for**:
  - Mass-scraping strangers' videos
  - Building derivative data products for resale or public redistribution
  - Bypassing rate limits, spoofing User-Agents, using proxy pools to evade
    anti-bot systems
  - High-frequency automation (e.g. daily full re-scans of the same channel)
  - Harassment, doxxing, coordinated attacks, or targeting specific users
- 📜 **Comply with Bilibili's ToS** and [robots.txt](https://www.bilibili.com/robots.txt).
  For commercial/organization use, switch to the official
  [Bilibili Open Platform](https://openhome.bilibili.com/) APIs.
- 🔒 **Data minimization**: fetch → analyze → delete. Do not retain raw data
  long-term, and do not share files containing user IDs or IP locations.
- 🎯 **The tool is designed for one-shot analyses**, not long-term
  surveillance.

> This project is not affiliated with bilibili.com. Any account-level risk
> control, bans, or legal consequences are the user's responsibility. When
> in doubt about whether a specific use case is allowed — **don't run it**.

---

## Install

It is a plain, self-contained skill: Python 3.9+ stdlib only, zero pip
install. The skill lives in the Agents365-ai skills monorepo; clone the
monorepo and link or copy the skill directory into your agent's skills path:

```bash
# Global (Claude Code example; other agents read their own skills path)
git clone https://github.com/Agents365-ai/365-skills.git
ln -s "$(pwd)/365-skills/plugins/bbc/skills/bbc-skill" ~/.claude/skills/bbc-skill

# Project-level
ln -s "$(pwd)/365-skills/plugins/bbc/skills/bbc-skill" .claude/skills/bbc-skill
```

Or run it standalone without any skill runtime:

```bash
git clone https://github.com/Agents365-ai/365-skills.git
cd 365-skills/plugins/bbc/skills/bbc-skill
python3 -m bbc --help
```

---

## Quick start

### Step 1 · Export your Bilibili cookie

Bilibili's comment API rate-limits and returns thin data for unauthenticated
requests. For full UP主 analysis you must authenticate with a cookie.

**Recommended**: the open-source Chrome extension
[**Get cookies.txt LOCALLY**](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
— runs entirely locally, uploads nothing.

1. Install **Get cookies.txt LOCALLY** from the Chrome Web Store.
2. Visit [https://www.bilibili.com](https://www.bilibili.com) and confirm you
   are logged in (avatar visible top-right).
3. Click the extension icon → **Export** → download
   `www.bilibili.com_cookies.txt`.
4. Save it somewhere convenient, e.g. `~/Downloads/bilibili_cookies.txt`.

**Other options**:

- Firefox: [cookies.txt](https://addons.mozilla.org/firefox/addon/cookies-txt/)
  add-on.
- Edge: the same Chrome extension works.
- Manual: DevTools F12 → Application → Cookies → copy the `SESSDATA` value,
  then `export BBC_SESSDATA="<value>"`.

**Do not share `SESSDATA`** — it authorizes full account access.

### Step 2 · Verify the cookie works

```bash
./scripts/bbc cookie-check --cookie-file ~/Downloads/bilibili_cookies.txt
```

Expected:

```json
{"ok": true, "data": {"mid": 441831884, "uname": "探索未至之境", "vip": true, "level": 5, ...}}
```

If it fails: confirm you are currently logged in at bilibili.com, re-export
the cookie, and retry.

### Step 3 · Fetch comments

```bash
./scripts/bbc fetch BV1NjA7zjEAU \
  --cookie-file ~/Downloads/bilibili_cookies.txt
```

URLs are accepted too:

```bash
./scripts/bbc fetch "https://www.bilibili.com/video/BV1NjA7zjEAU/"
```

Output lives in `./bilibili-comments/BV1NjA7zjEAU/`:

```
bilibili-comments/BV1NjA7zjEAU/
├── comments.jsonl      # flat JSONL — one comment per line
├── summary.json        # video meta + aggregated stats + top-N
├── raw/                # archived API responses
└── .bbc-state.json     # resume / incremental state
```

---

## Environment variables

```bash
export BBC_COOKIE_FILE="$HOME/Downloads/bilibili_cookies.txt"
./scripts/bbc fetch BV1NjA7zjEAU
```

Or pass `SESSDATA` directly:

```bash
export BBC_SESSDATA="<value from DevTools>"
./scripts/bbc fetch BV1NjA7zjEAU
```

---

## Analysis workflow with Claude Code

After fetch completes, ask Claude something like:

> Read `./bilibili-comments/BV1NjA7zjEAU/summary.json` first — give me the
> overall picture: video stats, comment distribution, top 20 liked. Then
> I'll direct what to analyze next.

Claude follows this path:

1. **Read `summary.json` first** (a few KB) — video title, stats, time
   distribution, IP distribution, top-N comments.
2. **Sample `comments.jsonl` on demand** — each line is a flat JSON record;
   `Grep` for keywords, `head/tail` for chronology, sort by `like` for
   hot-comment analysis.
3. **Typical analyses**:
   - Sentiment: positive / negative / neutral ratio
   - Keyword frequency (excluding stopwords)
   - UP interaction audit: filter `is_up_reply=true`, see which threads you
     replied to vs. missed
   - Geographic breakdown from `ip_location`
   - Feedback evolution: bucket `ctime_iso` by week/month
   - Super-fan detection: group by `mid`, rank by comment count
   - Negative-review triage: high `like` + negative keywords

---

## Commands

### `bbc fetch <BV|URL>`

```
--max N                 Cap top-level comments (default: all)
--since <date>          Only fetch comments newer than this (ISO, e.g. 2026-04-01)
--output <dir>          Output directory (default ./bilibili-comments/<BV>/)
--cookie-file <path>    Netscape cookie file
--browser <name>        auto / firefox / chrome / edge / safari
--format json|table     stdout format
--dry-run               Preview request plan, no network calls
--force                 Ignore resume state, refetch everything
```

### `bbc fetch-user <UID>`

Batch fetch across a UP主's entire video catalog, sequential with a randomised
5-10s cooldown between videos.

```bash
python3 -m bbc fetch-user 441831884 --cookie-file cookies.txt
python3 -m bbc fetch-user 441831884 --video-limit 2   # dry-run / small batches
```

### `bbc summarize <dir>`

Rebuild `summary.json` from an existing `comments.jsonl`.

### `bbc cookie-check`

Validate the cookie and print the logged-in user.

### `bbc schema [command]`

Return JSON schema for a command (param types, exit codes, error codes).

### Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Success |
| 1 | Runtime / API error |
| 2 | Auth error (cookie invalid / missing) |
| 3 | Validation error (bad parameter) |
| 4 | Network error (timeout / retries exhausted) |

---

## Output schemas

### `comments.jsonl` record

```json
{
  "rpid": 296636680849,
  "bvid": "BV1NjA7zjEAU",
  "parent": 0,
  "root": 0,
  "mid": 71171081,
  "uname": "user nickname",
  "user_level": 4,
  "vip": false,
  "ctime": 1776521119,
  "ctime_iso": "2026-04-18T06:25:19+00:00",
  "message": "...",
  "like": 1,
  "rcount": 0,
  "ip_location": "河北",
  "is_up_reply": false,
  "top_type": 0,
  "mentioned_users": [],
  "jump_urls": []
}
```

- `parent=0` → top-level; otherwise `rpid` of the parent comment
- `top_type`: 0=normal, 1=UP pinned, 2=editor pinned
- `is_up_reply`: true if the comment was authored by the video owner

### `summary.json` fields

- `video`: title, description, stats, tags, cover URL, owner
- `counts`: total, top-level, nested, pinned, unique users, UP replies,
  completeness ratio
- `time_distribution`: earliest/latest timestamps, daily histogram
- `top_liked`: top-N comments by like count
- `top_replied`: top-N top-level comments by reply count
- `ip_distribution`: histogram of IP provinces

See `references/agent-contract.md` for the full schema.

---

## Limits & caveats

- **Read-only** — never posts, edits, or deletes. Safety tier: `open`.
- **Rate** — 1s between top-level requests, 0.5s for nested. ~5000 comments
  takes 10-15 minutes.
- **Anti-bot** — HTTP 412 triggers exponential backoff (3 retries).
- **Completeness** — the `completeness` field in `summary.json` compares
  fetched vs. declared counts; values below 1.0 indicate deleted comments
  or API inconsistency.
- **Anonymous not supported** — UP主 analysis requires a valid cookie.

---

## References

- [SKILL.md](./SKILL.md) — skill trigger + usage guide for Claude
- [references/api-endpoints.md](./references/api-endpoints.md) — Bilibili
  API fields used
- [references/agent-contract.md](./references/agent-contract.md) — envelope /
  exit code / schema contract

---

## Contributing

Suggestions, bug reports, and pull requests are all welcome. If you have
ideas — new analysis workflows, better anti-bot defaults, additional
platform support, documentation fixes — feel free to
[open an issue](https://github.com/Agents365-ai/365-skills/issues) or
submit a PR directly.

This skill is community-friendly: every contribution, no matter how small,
helps make it better for everyone.

---

## Support

If this skill helps you, consider supporting the author:

<table>
  <tr>
    <td align="center">
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/qrcode/wechat-pay.png" width="180" alt="WeChat Pay">
      <br>
      <b>WeChat Pay</b>
    </td>
    <td align="center">
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/qrcode/alipay.png" width="180" alt="Alipay">
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

## Author

**Agents365-ai** &mdash; building open-source skills for AI coding agents.

- Bilibili: <https://space.bilibili.com/441831884>
- GitHub: <https://github.com/Agents365-ai>

---

## License

MIT
