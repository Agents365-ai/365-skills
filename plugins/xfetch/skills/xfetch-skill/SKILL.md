---
name: xfetch
description: Fetch and export public X (Twitter) data with a self-contained Python CLI built on the twikit library — no developer API keys, just the user's own login cookies. Covers user profiles, a user's tweets/replies/likes, single tweets, threads, search, followers/following, home/bookmark timelines, with JSON/JSONL/CSV/SQLite output and resumable pagination. Use whenever the user wants to scrape, download, collect, archive, monitor, or analyze tweets or X/Twitter accounts, export a timeline or follower list to a file or dataset, pull X data for research, or build a tweet corpus — even if they don't name the tool. Requires the user's own X login cookies (auth_token + ct0, or username/password login).
license: MIT
compatibility: Requires Python >= 3.10 and the twikit package (pip install twikit). Needs the user's own X/Twitter session cookies.
platforms: [macos, linux, windows]
metadata: {"openclaw":{"requires":{"bins":["python3"]},"emoji":"🐦","os":["darwin","linux","win32"]}}
---

# xfetch

Fetch **public** data from X (Twitter) — profiles, tweets, threads, search, followers — using the user's own login cookies instead of the paid developer API. This skill ships a single self-contained CLI, `scripts/xfetch.py`, that calls X's GraphQL API directly and emits structured data an agent can parse.

**How it stays working (the architecture that matters):** the hard part of X scraping is that X constantly changes its site — it rotates GraphQL query IDs every few weeks, migrates endpoints between GET and POST, and reshapes response JSON. This CLI splits those concerns so a break in one place doesn't take everything down:

- It **reuses the current query IDs and feature flags** shipped by the [twikit](https://github.com/d60/twikit) package (kept fresh with `pip install -U twikit`) — so you don't hand-maintain the fastest-rotating values.
- It does its **own HTTP requests and JSON parsing**, which sidesteps the two things most likely to be broken in twikit at any moment: (1) its homepage-scraped anti-bot transaction ID — this CLI sends a harmless placeholder `x-client-transaction-id`, which X accepts for read endpoints; and (2) its response-model layer — this CLI parses the raw JSON itself. It also auto-falls-back GET↔POST on a 404, so an endpoint X migrates keeps working.

Net: if a command suddenly errors for everyone, the first fix is still `pip install -U twikit` (refreshes query IDs). If that doesn't help, X changed a response shape — check the parser in `scripts/xfetch.py`.

## The agent-native contract

`scripts/xfetch.py` is built so you can drive it in a loop without surprises. Rely on these three channels rather than scraping prose:

- **`stdout`** carries the data payload only (JSON by default). Redirect or pipe it — nothing else is written there.
- **`stderr`** carries human status (`✓ Saved…`) and errors. Read it to diagnose; ignore it when parsing.
- **exit code** is the truth signal: `0` = success, `1` = error, `2` = not authenticated, `3` = rate limited (stderr carries `rate_limit_reset=<epoch>`), `64` = usage error (bad flag or argument — fix the command, don't re-auth). Branch on the exit code, not on stderr text.

## Setup (once per environment)

1. **Confirm Python and install twikit** (a virtualenv is cleanest so you don't touch system packages):

   ```bash
   python3 -m pip install -r scripts/requirements.txt   # installs twikit>=2.3.3
   ```

2. **Verify the CLI loads:**

   ```bash
   python3 scripts/xfetch.py --version    # -> xfetch-skill 0.3
   ```

Invoke every command as `python3 scripts/xfetch.py <command> …` using this skill's own copy of the script.

## Authenticate first — this is the #1 failure mode

Every data command needs the user's X cookies (`auth_token` + `ct0`). Without them the command prints `Not authenticated.` to stderr and **exits 2**. Auth is **delegated**: the human sets it up once, the CLI saves a session to `~/.config/xfetch/cookies.json`, and you reuse it — you don't own the credential lifecycle, you just check it's present.

**Always run this first** and branch on the exit code:

```bash
python3 scripts/xfetch.py auth check
```

If it isn't authenticated, get the human to provide credentials, in order of preference:

- **Extract from a logged-in browser** (most convenient — reads the x.com cookies straight from the browser's store, no copy/paste):

  ```bash
  python3 scripts/xfetch.py auth extract --browser chrome
  # supported: chrome, chromium, firefox, safari, edge, brave, arc, opera, vivaldi, librewolf
  ```

  Requires `browser_cookie3` (in `requirements.txt`). On macOS this may prompt for Keychain access — that's the OS handing over the cookie-decryption key, which is expected.
- **Import a cookies file** (best for browsers without a reader — e.g. **ChatGPT Atlas**, Orion, or any Chromium fork): export cookies with a "Get cookies.txt" browser extension (Netscape `cookies.txt` or JSON both work), then point the CLI at the file — it extracts `auth_token` + `ct0` for you:

  ```bash
  python3 scripts/xfetch.py auth import --file ~/Downloads/x.com_cookies.txt
  ```

- **Paste cookie tokens** (works for any browser): open DevTools → Application → Cookies → `https://x.com`, copy the `auth_token` and `ct0` values, then:

  ```bash
  python3 scripts/xfetch.py auth set --auth-token <token> --ct0 <token>
  ```

- **Environment variables** (good for CI / one-off, saves nothing to disk):

  ```bash
  XFETCH_AUTH_TOKEN=<token> XFETCH_CT0=<token> python3 scripts/xfetch.py user @handle
  ```

- **Username/password login** (twikit performs a real login; may trip a captcha or 2FA — pass `--totp` for TOTP-based 2FA):

  ```bash
  python3 scripts/xfetch.py auth login --username <user> --password <pass>
  ```

Never invent or guess cookie values. Prefer `auth set`/env over `login` so no password passes through the command line. If auth is missing and you can't obtain it, stop and ask the human — you cannot proceed without it. These read a real account, so its login is a shared, rate-limited resource: don't hammer it.

## Choose the output format for the consumer

The default `json` is pretty-printed for a human reading one result. For anything you or a pipeline will parse, pick deliberately with `--format`:

| Format | Flag | Use when |
| -------- | ------ | ---------- |
| JSON (pretty) | *(default)* | Inspecting a single object or a small result |
| JSONL | `--format jsonl` | Large / multi-page results — one record per line, appendable, stream-friendly |
| CSV | `--format csv` | Spreadsheets or quick tabular analysis (nested fields are JSON-encoded in-cell) |
| SQLite | `--format sqlite --db out.db` | Building a queryable dataset; rows go to a `tweets`/`users` table, a summary prints to stderr |

Add `--plain` for compact single-line JSON. Save to a file by redirecting stdout, e.g. `… --format jsonl > tweets.jsonl`.

## Commands

```bash
# Profile (by @handle or numeric id)
python3 scripts/xfetch.py user @elonmusk

# A user's tweets (--replies for replies, --media for media-only)
python3 scripts/xfetch.py tweets @elonmusk -n 50
python3 scripts/xfetch.py tweets @elonmusk --replies --all --format jsonl > timeline.jsonl

# A user's liked tweets
python3 scripts/xfetch.py likes @handle -n 40

# Single tweet, and a tweet with its replies (thread)
python3 scripts/xfetch.py tweet https://x.com/user/status/1234567890
python3 scripts/xfetch.py thread 1234567890

# Search (--type top|latest|media)
python3 scripts/xfetch.py search "AI agents" -n 100 --type latest
python3 scripts/xfetch.py search "from:openai since:2024-01-01" --all --format csv > openai.csv

# Followers / following, paginated into a SQLite dataset
python3 scripts/xfetch.py followers @handle --all --format sqlite --db network.db
python3 scripts/xfetch.py following @handle -n 100

# Your own timelines (uses the logged-in account)
python3 scripts/xfetch.py home              # "For You"
python3 scripts/xfetch.py home --following  # chronological
python3 scripts/xfetch.py bookmarks -n 50
```

`search` supports X's advanced operators (`from:`, `to:`, `since:`, `until:`, `filter:`, `min_faves:`, etc.) — pass them inside the quoted query. For the full flag reference and the exact fields each command returns, read `references/commands.md`.

DMs, lists, and trends are not exposed as commands (to keep this CLI small), but twikit supports them (`get_dm_history`, `get_list_tweets`, `get_trends`) — add a command following the existing pattern in `scripts/xfetch.py` if the user needs one.

## Pagination and rate limits

Listing commands (`tweets`, `search`, `followers`, `following`, `likes`, `home`, `bookmarks`) share these flags — single page by default, opt into more:

```bash
-n 40            # results per page
--all            # every page until exhausted
--max-pages 10   # cap the pages
--cursor <c>     # start from a specific pagination cursor
--delay 1.5      # seconds between pages (default 1.0 — keep it >0 for --all)
```

When more pages remain — or a pull is interrupted or rate limited mid-way — the CLI prints `next_cursor=<value>` to stderr. Capture it and pass it back via `--cursor` to resume exactly where the pull stopped instead of refetching from the top.

X enforces per-account rate limits (roughly a few hundred requests per 15-minute window per endpoint) and this uses the user's real account. For bulk pulls keep a real `--delay`, prefer `--max-pages` over `--all` when you only need a sample, and remember aggressive scraping can get the account throttled or flagged. Route through a proxy for heavier work with `--proxy http://user:pass@host:port`.

## When something fails

Check the exit code, then read stderr to classify:

- **exit 2 / `Not authenticated`** → run the auth flow above.
- **exit 64 / usage error** → the command line itself is wrong (unknown flag, bad value). Fix the invocation — do **not** re-run auth.
- **exit 3 / rate limited** → stderr carries `rate_limit_reset=<epoch>`; wait until then, raise `--delay`, and resume from the `next_cursor=` value printed on stderr.
- **exit 1 with a GraphQL / parsing error that started suddenly for everyone** → X likely changed its site. Upgrade twikit (`pip install -U twikit`) and retry.
- **Timeout / network errors mid-pull** → resume from the `next_cursor=` line on stderr instead of refetching from the top.
- **Empty result** → the account may be private (you only see what the logged-in account can), suspended, or the handle is wrong.

## Scope and good-citizen notes

This reads **public** data plus whatever the logged-in account can see (its own home, bookmarks, likes). It does **not** post, like, follow, or modify anything — it's read-only by design. Because it uses the user's own session, the user is responsible for staying within X's Terms of Service and rate limits. Use it for legitimate purposes — research, personal archiving, monitoring accounts the user is entitled to read — not for harassment, mass surveillance, or evading a block. Session cookies live under `~/.config/xfetch/`; clear them with `auth clear`.
