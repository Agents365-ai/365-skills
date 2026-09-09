# xfetch 🐦

Fetch and export **public** X (Twitter) data with a self-contained Python CLI built on
[twikit](https://github.com/d60/twikit) — no developer API keys, just your own login
cookies. Profiles, a user's tweets/replies/likes, single tweets, threads, search,
followers/following, and your home/bookmark timelines, exported as **JSON / JSONL / CSV /
SQLite** with resumable pagination.

It's packaged as a [Claude Code](https://docs.claude.com/en/docs/claude-code) /
[OpenClaw](https://openclaw.ai) **skill** — the agent instructions live in
[`SKILL.md`](SKILL.md) — but `scripts/xfetch.py` is a plain CLI you can run on its own.

## Why it keeps working

X rotates its GraphQL query IDs, migrates endpoints between GET and POST, and reshapes
response JSON constantly. `xfetch` splits those concerns so one break doesn't sink
everything:

- **Query IDs + feature flags** come from twikit (refresh with `pip install -U twikit`) —
  you don't hand-maintain the fastest-rotating values.
- **HTTP and JSON parsing are its own**, sidestepping the parts of twikit most often broken:
  it sends a harmless placeholder `x-client-transaction-id` (X accepts it for read
  endpoints), parses raw JSON itself, and **auto-falls-back GET↔POST on a 404**.

## Requirements

- Python ≥ 3.10
- `pip install -r scripts/requirements.txt` (installs `twikit`; `browser_cookie3` for
  browser cookie extraction)
- Your own X login cookies (`auth_token` + `ct0`), or username/password login

## Quick start

```bash
python3 -m pip install -r scripts/requirements.txt
python3 scripts/xfetch.py --version

# Authenticate once (pick one) — saves to ~/.config/xfetch/cookies.json
python3 scripts/xfetch.py auth extract --browser chrome     # read cookies from a logged-in browser
python3 scripts/xfetch.py auth set --auth-token <t> --ct0 <t>   # or paste tokens
python3 scripts/xfetch.py auth check                        # verify (exit 0 = ok, 2 = not authed)

# Fetch
python3 scripts/xfetch.py user @elonmusk
python3 scripts/xfetch.py tweets @elonmusk --all --format jsonl > timeline.jsonl
python3 scripts/xfetch.py search "AI agents" -n 100 --type latest
python3 scripts/xfetch.py followers @handle --all --format sqlite --db network.db
```

Supported extract browsers: `chrome, chromium, firefox, safari, edge, brave, arc, opera,
vivaldi, librewolf`. For browsers without a reader, export a cookies file and use
`auth import --file …`, or paste tokens with `auth set`.

## Agent-native contract

Drive it in a loop without scraping prose:

- **stdout** — data payload only (JSON by default; `--format jsonl|csv|sqlite`).
- **stderr** — human status and errors.
- **exit code** — `0` ok · `1` error · `2` not authenticated · `3` rate limited
  (stderr carries `rate_limit_reset=<epoch>`) · `64` usage error.

When pages remain or a pull is interrupted, `next_cursor=<value>` is printed to stderr —
pass it back via `--cursor` to resume exactly where it stopped.

Full command + flag reference: [`references/commands.md`](references/commands.md).

## Scope

Read-only by design: it reads **public** data plus whatever the logged-in account can see
(its own home, bookmarks, likes). It never posts, likes, follows, or modifies anything.
Because it uses your own session, you are responsible for staying within X's Terms of
Service and rate limits — use it for research, personal archiving, and monitoring accounts
you're entitled to read. Clear the saved session with `auth clear`.

## License

MIT
