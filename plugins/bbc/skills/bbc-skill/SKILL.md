---
name: bbc-skill
description: Fetch Bilibili (哔哩哔哩) video comments for UP主 self-analysis. Use when the user asks to collect, download, export, or analyze comments on a Bilibili video (BV号 / URL / UID). Produces JSONL + summary.json suitable for further Claude Code analysis (sentiment, keywords, audience trends). Read-only; does not post/edit/delete.
license: MIT
homepage: https://github.com/Agents365-ai/bbc-skill
metadata: {"version":"1.0.4","openclaw":{"requires":{"bins":["python3"]},"emoji":"💬"},"hermes":{"category":"data","tags":["bilibili","comments","up主","scraping","chinese"]}}
---

# bbc-skill — Bilibili Comment Collector

Download all comments (top-level + nested + pinned) for a Bilibili video and
produce data that Claude Code can analyze downstream.

## Update check

Throttle to one check per 24 hours per installation; never mutate the skill directory without explicit user consent.

1. If `<this-skill-dir>/.last_update` exists and is less than 24 hours old, skip this step entirely.

2. Otherwise, fetch the latest tag from upstream:

   ```bash
   git -C <this-skill-dir> ls-remote --tags origin 'v*' 2>/dev/null \
     | awk '{print $2}' | sed 's|refs/tags/||' \
     | sort -V | tail -1
   ```

3. Compare with this skill's `metadata.version` from the frontmatter. If the upstream tag is strictly newer (semver), tell the user one line and ask:

   > "A newer version of this skill is available: vX.Y.Z → vA.B.C. Want me to `git pull`?"

   If they say yes, run `git -C <this-skill-dir> pull --ff-only`. Refresh `.last_update` either way so the prompt doesn't repeat for 24 hours.

4. If upstream is the same or older, refresh `.last_update` silently and continue.

5. On any failure (offline, not a git checkout — e.g. ClawHub-installed copy, read-only path, no permission), swallow the error silently and continue with the user's task. Do not mention the failure.

## When to use

Trigger this skill when the user:

- Asks to **get / fetch / download / export / collect / analyze** comments of a
  specific Bilibili video (BV 号, URL, or video page).
- Asks to analyze **audience feedback / sentiment / keywords / top comments /
  IP distribution** of their own Bilibili videos.
- Provides a Bilibili URL like `https://www.bilibili.com/video/BVxxxxxxxxxx/`.
- Mentions their UP主 UID and wants batch analysis across their videos.

Do **not** use for: posting / deleting comments, downloading videos, barrage
(弹幕), live stream data, or private messages.

## Prerequisites

1. **Python 3.9+** (stdlib only — zero pip install).
2. **Bilibili cookie**. The user must be logged in to bilibili.com. The
   recommended path:
   - Install the Chrome/Edge extension
     [**Get cookies.txt LOCALLY**](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
     (open-source, fully local, no upload).
   - On a logged-in bilibili.com tab, click **Export** → save
     `www.bilibili.com_cookies.txt`.
   - Pass via `--cookie-file` or set `$BBC_COOKIE_FILE`.

   Alternatives:
   - `$BBC_SESSDATA` env var with just the SESSDATA value.
   - Browser auto-detection (Firefox / Chrome / Edge on macOS) via
     `--browser auto`. Works best for Firefox; Chrome/Edge needs a logged-in
     profile with cookies flushed to disk.

**Auth delegation (Principle 7):** the skill never runs OAuth flows. The human
is expected to log in via browser; the agent only consumes the resulting
cookie.

## Quick start

Before any fetch, verify the cookie works:

```bash
python3 -m bbc cookie-check
```

Success envelope (stdout):

```json
{"ok":true,"data":{"mid":441831884,"uname":"探索未至之境","vip":false}}
```

Fetch all comments for a single video:

```bash
python3 -m bbc fetch BV1NjA7zjEAU
```

Or pass a URL:

```bash
python3 -m bbc fetch "https://www.bilibili.com/video/BV1NjA7zjEAU/"
```

Output (default `./bilibili-comments/<BV>/`):

- `comments.jsonl` — one comment per line, flattened
- `summary.json` — video metadata + statistics + top-N
- `raw/` — archived API responses
- `.bbc-state.json` — resume state

## Commands

| Command | Purpose |
| --- | --- |
| `bbc fetch <BV\|URL>` | Fetch all comments for one video |
| `bbc fetch-user <UID>` | Batch fetch all videos of a UP主 |
| `bbc summarize <dir>` | Rebuild `summary.json` from existing `comments.jsonl` |
| `bbc cookie-check` | Validate cookie; print logged-in user |
| `bbc schema [cmd]` | Return JSON schema for commands (for agent discovery) |

Call `bbc <cmd> --help` or `bbc schema <cmd>` for full parameter details — do
not guess flag names.

## Agent contract

### Stdout vs stderr

- **stdout**: stable JSON envelope `{"ok":true,"data":...}` or
  `{"ok":false,"error":...}`. JSON is the default when stdout is not a TTY.
  Pass `--format table` for human-readable tables.
- **stderr**: human log lines + NDJSON progress events for long tasks.

### Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Success |
| 1 | Runtime / API error |
| 2 | Auth error (cookie invalid / missing) |
| 3 | Validation error (bad BV number, bad flag) |
| 4 | Network error (timeout / retries exhausted) |

### Error envelope

```json
{
  "ok": false,
  "error": {
    "code": "auth_expired",
    "message": "SESSDATA 已过期，请重新登录 B 站",
    "retryable": true,
    "retry_after_auth": true
  }
}
```

Error codes: `validation_error`, `auth_required`, `auth_expired`, `not_found`,
`rate_limited`, `api_error`, `network_error`. See `bbc schema` for the full
contract.

### Dry-run

Every fetch command supports `--dry-run` to preview the planned request
without making network calls:

```bash
python3 -m bbc fetch BV1NjA7zjEAU --dry-run
```

### Idempotency

Re-running the same `fetch` command on the same output directory resumes from
`.bbc-state.json` (skips already-fetched pages). Pass `--force` to refetch.

## Analysis workflow (for the agent)

After `fetch` completes:

1. **Read `summary.json` first** (< 10 KB) to establish global context: video
   metadata, total counts, time distribution, top-N.
2. **For thematic analysis**, `Grep` or `head`/`tail` on `comments.jsonl` —
   each line is a flat JSON object, never load the whole file unless small.
3. **Typical analyses**:
   - Sentiment distribution → scan `message` by batch
   - Top fans → group by `mid`, count entries, aggregate `like`
   - UP 主互动 → filter `is_up_reply=true`
   - Audience geography → `ip_location` histogram
   - Feedback timeline → bucket `ctime_iso` by day/week

The `summary.json` schema is documented in `references/agent-contract.md`.
Run the skill against any video to produce a real sample locally.

## Safety tier

All commands are **read-only** (tier: `open`). No mutation, no deletion, no
message sending. Dry-run available for all fetch commands.

## References

- `references/api-endpoints.md` — Bilibili API fields used
- `references/cookie-extraction.md` — per-browser cookie decryption
- `references/agent-contract.md` — full envelope + schema contract

## Limitations

- `all_count` returned by the API includes pinned comments. Completeness
  check: `top_level + nested + pinned == declared_all_count`.
- Very old comments (>2 years) may return thin data if the user was deleted.
- Anti-bot: aggressive `--max` values or repeated runs may trigger HTTP 412.
  The client sleeps 1s between requests and backs off on 412.
