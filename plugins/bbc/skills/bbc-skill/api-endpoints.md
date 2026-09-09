# Bilibili API endpoints used

All endpoints are HTTP GET with cookie auth. No official SDK — these are
reverse-engineered from the web client. They are stable in practice but
undocumented by Bilibili.

## 1. `GET /x/web-interface/view`

Convert `bvid` → `aid`, plus full video metadata.

**Params**

- `bvid` (required)

**Key response fields** (`data`)

- `bvid`, `aid`, `cid` — three ID forms
- `title`, `desc`, `dynamic` — textual content
- `pubdate`, `ctime` — Unix timestamps (seconds)
- `duration` — seconds
- `tname`, `tid` — category name and id
- `pic` — cover image URL
- `owner.mid`, `owner.name`, `owner.face` — UP主 info
- `stat.view`, `stat.like`, `stat.coin`, `stat.favorite`, `stat.reply`,
  `stat.danmaku`, `stat.share`, `stat.his_rank`, `stat.now_rank`
- `staff[]` — collaborative authors (empty if solo)

## 2. `GET /x/web-interface/nav`

Validate cookie / fetch logged-in user info.

**Key response fields** (`data`)

- `isLogin` — bool
- `mid`, `uname`
- `level_info.current_level`
- `vipStatus` — 0/1

Used by `bbc cookie-check`.

## 3. `GET /x/tag/archive/tags`

Fetch tags for a given BV.

**Params**

- `bvid` (required)

**Response**

- `data[]` with `tag_name`, `tag_id`

## 4. `GET /x/v2/reply/main` — top-level comments

Paginated top-level comments.

**Params**

- `type=1` — video (type=11 for article, etc. — not used here)
- `oid=<aid>` — Note: must use `aid`, not `bvid`
- `mode=3` — sort by time desc (mode=2 is hot)
- `next=<cursor>` — pagination cursor (0 for first page)
- `ps=20` — page size

**Key response fields** (`data`)

- `replies[]` — top-level comments
- `top_replies[]` — pinned comments (only on first page)
- `upper.top` — UP主 pinned comment (alternate location)
- `cursor.next` — next page cursor
- `cursor.is_end` — true when done
- `cursor.all_count` — total declared comment count

### Top-level reply fields used

| Path | Meaning |
| --- | --- |
| `rpid`, `rpid_str` | Unique comment id (use str for safe JSON) |
| `oid`, `oid_str` | Video aid |
| `mid`, `mid_str` | Commenter UID |
| `parent` | Parent rpid (0 for top-level) |
| `root` | Root rpid (0 for top-level) |
| `ctime` | Unix seconds |
| `like` | Like count |
| `rcount` | Nested reply count |
| `member.uname` | Display name |
| `member.level_info.current_level` | User level 0-6 |
| `member.sex` | "男" / "女" / "保密" |
| `member.vip.vipStatus` | 0/1 |
| `content.message` | Comment text |
| `content.members[]` | @-mentioned users |
| `content.jump_url` | Dict of URLs detected in comment |
| `reply_control.location` | `"IP属地：河北"` — strip prefix |
| `replies[]` | Inline preview of 1-3 nested replies (not exhaustive) |

## 5. `GET /x/v2/reply/reply` — nested replies

Full nested replies for a given top-level comment.

**Params**

- `type=1`
- `oid=<aid>`
- `root=<top-level rpid>`
- `pn=1` — page number (1-based)
- `ps=20`

**Response**

- `data.replies[]` — nested replies (same schema as top-level, with
  `parent`/`root` populated)

Call this for every top-level comment where `rcount > 0`. Stop when the
returned page has `< 20` replies.

## 6. `GET /x/space/wbi/arc/search` — UP主 video list

List a user's videos (for `fetch-user` batch mode).

**Params**

- `mid=<uid>`
- `pn=1`, `ps=50`
- `order=pubdate` — sort by publish date

**Caveat**: this endpoint requires **WBI signing** (MD5 of sorted params +
mixin key derived from `/x/web-interface/nav`). The current fetcher is
single-video only; `fetch-user` ships in a later release.

## Error codes observed

| `code` | Meaning | Action |
| --- | --- | --- |
| `0` | OK | Proceed |
| `-101` | Account not logged in | Re-auth (auth_expired) |
| `-111` | CSRF token invalid | Re-auth |
| `-352` | Risk control triggered | Retry with backoff |
| `-412` | Rate limited (request) | Retry with backoff |
| `-509` | Overloaded | Retry with backoff |
| `62002` | Comment area closed | not_found |
| `-404`, `62004` | Resource not found | not_found |

## Pagination details

- **`/x/v2/reply/main`** uses **cursor-based** pagination. `cursor.next` on
  the current response is the `next` param for the next request. Start with
  `next=0`. Stop when `cursor.is_end=true` or `replies=[]`.
- **`/x/v2/reply/reply`** uses **page-number** pagination (`pn=1, 2, ...`).
  Stop when returned `replies` has fewer than `ps` entries.

## Completeness invariant

The first-page `cursor.all_count` equals:

```
top_level_count + nested_count + pinned_count
```

Use this as a self-check after fetching everything — see the
`completeness` field in `summary.json`. A value below 1.0 usually means
comments were deleted between pages or a nested page returned
inconsistent `rcount`.
