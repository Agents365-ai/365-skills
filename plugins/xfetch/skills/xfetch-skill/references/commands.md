# xfetch command reference

Full flag reference and output fields for `scripts/xfetch.py`. Invoke as
`python3 scripts/xfetch.py <command> [options]`. See `SKILL.md` for setup, auth,
and the agent-native output contract.

## Global options (accepted by every command)

| Flag | Meaning |
| ------ | --------- |
| `--cookies <path>` | Cookies file to load/save (default `~/.config/xfetch/cookies.json`, or `$XFETCH_COOKIES`) |
| `--auth-token <token>` | `auth_token` cookie for this run (pairs with `--ct0`) |
| `--ct0 <token>` | `ct0` cookie for this run |
| `--proxy <url>` | Route requests through a proxy, e.g. `http://user:pass@host:port` |
| `--format json\|jsonl\|csv\|sqlite` | Output format (default `json`) |
| `--db <path>` | SQLite database path (required with `--format sqlite`) |
| `--plain` | Compact single-line JSON (no indentation) |

Environment variables: `XFETCH_COOKIES`, `XFETCH_AUTH_TOKEN`, `XFETCH_CT0`,
`XFETCH_PROXY`, `XFETCH_TIMEOUT` (seconds, default 30), and
for `auth login`: `X_USERNAME`, `X_PASSWORD`, `X_EMAIL`, `X_TOTP_SECRET`.

## Pagination options (listing commands only)

Apply to `tweets`, `likes`, `search`, `followers`, `following`, `home`, `bookmarks`.

| Flag | Meaning |
| ------ | --------- |
| `-n, --count <n>` | Results per page (default 20) |
| `--all` | Fetch every page until exhausted |
| `--max-pages <n>` | Stop after N pages |
| `--cursor <c>` | Start from a specific pagination cursor |
| `--delay <seconds>` | Delay between pages (default 1.0; keep > 0 for `--all`) |

Single page is fetched when neither `--all` nor `--max-pages` is given.

When more pages remain — or a pull fails, is interrupted, or is rate limited
mid-way — the CLI prints `next_cursor=<value>` on stderr. Pass that value back
via `--cursor` to resume where the pull stopped.

## Exit codes

| Code | Meaning |
| ------ | --------- |
| 0 | Success |
| 1 | Error (network, parsing, X-side change) |
| 2 | Not authenticated / credentials invalid |
| 3 | Rate limited (HTTP 429) — stderr carries `rate_limit_reset=<epoch>` |
| 64 | Usage error (unknown flag, bad argument value) |
| 130 | Interrupted (Ctrl-C) |

## auth — authentication

| Command | Purpose |
| --------- | --------- |
| `auth check` | Verify the saved/passed credentials by reading the authenticated home timeline. Prints `{"authenticated": …}` to stdout; exit 0 if valid, 2 if not. |
| `auth extract --browser <name>` | Read x.com cookies from a logged-in browser (`chrome`, `chromium`, `firefox`, `safari`, `edge`, `brave`, `arc`, `opera`, `vivaldi`, `librewolf`) and save them. Needs `browser_cookie3`; may prompt for Keychain on macOS. Not available for browsers without a reader (e.g. ChatGPT Atlas) — use `auth import` / `auth set` for those. |
| `auth import --file <path>` | Extract `auth_token` + `ct0` from a browser cookie export (Netscape `cookies.txt` or JSON) and save them. Best for browsers without a reader (ChatGPT Atlas, etc.). |
| `auth set --auth-token <t> --ct0 <t>` | Save cookie tokens to the cookies file. Works for any browser — copy `auth_token`/`ct0` from DevTools → Application → Cookies. |
| `auth login --username <u> --password <p> [--email <e>] [--totp <secret>]` | Perform a real X login via twikit and save the session. May hit a captcha/2FA. |
| `auth clear` | Delete the saved cookies file. |

## Data commands

| Command | Args | Extra flags | Returns |
| --------- | ------ | ------------- | --------- |
| `user <handle>` | `@handle` or numeric id | — | one **user** object |
| `tweets <handle>` | `@handle` or id | `--replies`, `--media` | list of **tweet** objects |
| `likes <handle>` | `@handle` or id | *(paginated)* | list of **tweet** objects the user liked |
| `tweet <url-or-id>` | tweet URL or id | — | one **tweet** object |
| `thread <url-or-id>` | tweet URL or id | — | list of **tweet** objects: root tweet followed by its replies |
| `search <query>` | quoted query string | `--type top\|latest\|media` | list of **tweet** objects |
| `followers <handle>` | `@handle` or id | *(paginated)* | list of **user** objects |
| `following <handle>` | `@handle` or id | *(paginated)* | list of **user** objects |
| `home` | — | `--following` (chronological) | list of **tweet** objects from your timeline |
| `bookmarks` | — | *(paginated)* | list of **tweet** objects you bookmarked |

`<handle>` accepts a `@name`, a bare `name`, or a numeric user id. `<url-or-id>`
accepts a numeric tweet id or any `.../status/<id>` or `.../article/<id>` URL.

### Search operators

`search` passes the query straight to X, so its advanced operators work inside
the quoted string: `from:user`, `to:user`, `@user`, `since:YYYY-MM-DD`,
`until:YYYY-MM-DD`, `filter:media|links|replies|verified`, `min_faves:N`,
`min_retweets:N`, `lang:en`, `"exact phrase"`, `-exclude`, `(a OR b)`.
Example: `search "from:openai (gpt OR sora) since:2024-01-01 min_faves:100" --type latest`.

## Output fields

### tweet object

`id`, `url`, `created_at`, `text` (longform note text when present, else full text),
`lang`, `favorite_count`, `retweet_count`, `reply_count`, `quote_count`,
`bookmark_count`, `view_count`, `is_quote_status`, `possibly_sensitive`,
`in_reply_to`, `conversation_id`, `hashtags`, `urls` (expanded),
`media` (`[{type, url}]`), `quote_id`, `retweeted_id`,
`author` (`{id, screen_name, name}`).

### user object

`id`, `screen_name`, `name`, `description`, `location`, `url`, `created_at`,
`followers_count`, `following_count`, `statuses_count`, `favourites_count`,
`media_count`, `listed_count`, `verified`, `is_blue_verified`, `protected`,
`profile_image_url`, `profile_banner_url`.

In CSV and SQLite output, nested fields (`hashtags`, `urls`, `media`, `author`)
are JSON-encoded within their cell/column. The SQLite table is named `tweets`
or `users` based on the data shape, or `records` otherwise. Rows are keyed on
`id` (`INSERT OR REPLACE`), so re-running or resuming a pull into the same
database does not create duplicate rows.

## Extending

This CLI exposes a read-only subset. Write actions (post/like/retweet/follow/
send-DM) are intentionally omitted, and read endpoints like lists, DMs,
communities, trends, retweeters/favoriters, and blue-verified-followers aren't
wired up yet — but the plumbing makes them cheap to add. To add a timeline-style
command:

1. Find the query-id constant in `twikit.client.gql.Endpoint` (e.g. `LIST_LATEST_TWEETS_TIMELINE`).
2. Copy the `variables` dict from the matching method in twikit's `gql.py`.
3. Write a handler like `cmd_bookmarks` that calls
   `paginate(args, at, ct0, Endpoint.X, variables, "tweet")` (or `"user"`), and
   register it in `build_parser`.

The shared `gql()` requester (placeholder transaction ID, GET↔POST fallback),
`extract_timeline` (entry walking, cursor, ad filtering), and `paginate` handle
the rest. Single-object endpoints (like a single tweet or user) call `gql()`
directly and pass the result through `parse_tweet` / `parse_user`.
