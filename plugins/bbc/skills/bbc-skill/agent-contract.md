# Agent contract

bbc-skill is designed per the **agent-native CLI** principles: one CLI
must serve humans, AI agents, and orchestrators simultaneously.

## Channels

| Channel | Content |
| --- | --- |
| `stdout` | JSON envelope (one command → one final envelope). Table rendering when stdout is a TTY. |
| `stderr` | Human log lines + NDJSON progress events for long tasks. |
| exit code | Numeric class of outcome (see below). |

## Stdout format auto-detection

- If stdout is **not** a TTY (piped / captured / redirected): JSON (one line)
- If stdout **is** a TTY: human-readable table / indented JSON
- Override with `--format json` or `--format table`

Agents redirecting output to a file or capturing via `stdout=PIPE` will
automatically receive parseable JSON without any flag.

## Envelope (success)

```json
{
  "ok": true,
  "data": { ... },
  "meta": {
    "request_id": "req_xxx",
    "latency_ms": 12345,
    "schema_version": "1.0.0"
  }
}
```

For dry-run commands a top-level `dry_run: true` is also set.

## Envelope (failure)

```json
{
  "ok": false,
  "error": {
    "code": "auth_expired",
    "message": "Cookie 已过期，请重新登录 Bilibili。",
    "retryable": true,
    "retry_after_auth": true
  },
  "meta": { ... }
}
```

### Error codes

| `code` | Exit | Retryable | Meaning |
| --- | --- | --- | --- |
| `validation_error` | 3 | no | Bad BV number, bad flag, bad date format |
| `auth_required` | 2 | yes (after login) | No cookie available |
| `auth_expired` | 2 | yes (after login) | Cookie rejected by B站 |
| `not_found` | 1 | no | Video deleted / comment area closed |
| `rate_limited` | 1 | yes (after backoff) | HTTP 412 / code=-352 / -412 / -509 |
| `api_error` | 1 | no | B站 returned non-zero `code` |
| `network_error` | 4 | yes | Timeout / DNS / retries exhausted |
| `internal_error` | 1 | no | Bug in the skill — please file an issue |

### Retry protocol

- `retryable: false` → do not retry; treat as terminal.
- `retryable: true` without `retry_after_auth` → safe to retry immediately
  after backoff.
- `retryable: true` with `retry_after_auth: true` → prompt the human to
  re-authenticate (re-export cookie), then retry.

## NDJSON progress events (stderr)

Emitted when `BBC_PROGRESS=1` or when stderr is a TTY. One JSON object per
line. Schema:

```json
{"event": "start",    "command": "fetch", "request_id": "...", "elapsed_ms": 0, "bvid": "..."}
{"event": "progress", "command": "fetch", "request_id": "...", "elapsed_ms": 2294, "phase": "meta", "title": "..."}
{"event": "progress", "command": "fetch", "request_id": "...", "elapsed_ms": 3437, "phase": "top_level", "page": 2, "done": 20, "cumulative": 39, "declared_total": 59}
{"event": "progress", "command": "fetch", "request_id": "...", "elapsed_ms": 6186, "phase": "nested", "root_rpid": 299313655152, "page": 1, "got": 1, "cumulative_subs": 1}
{"event": "complete", "command": "fetch", "request_id": "...", "elapsed_ms": 12237, "counts": {"total": 59, "top_level": 44, "nested": 14, "pinned": 1}}
```

### Phases

- `meta` — video metadata fetched (BV→aid resolved)
- `top_level` — a top-level comment page was fetched
- `nested` — nested replies for a top-level comment were fetched
- `warn` — non-fatal warnings (e.g. decryption fallback)

Suppression: `BBC_PROGRESS=0` disables progress events.

## Schema introspection

```
$ bbc schema
{"ok": true, "data": {"schema_version": "1.0.0", "commands": {...}, ...}}

$ bbc schema fetch
{"ok": true, "data": {"command": "fetch", "params": {...}, "envelope": {...}, ...}}
```

The schema output is the source of truth for:

- Parameter types and defaults
- Exit code mapping
- Error codes and their retryability

An agent can discover the CLI surface without reading this README.

## Idempotency

All fetch commands are idempotent within an output directory:

- Re-running with the same `--output` reuses `.bbc-state.json` and resumes
- Pass `--force` to discard state and refetch
- Same `--since <date>` on repeated runs → incremental monitor mode

There is no `--idempotency-key` flag because:

- The command is read-only (no mutation on the server side)
- The output directory + resume state serves the same purpose for local
  correctness

## Auth delegation

The skill **never** runs a browser OAuth flow. The human is responsible
for:

- Logging into bilibili.com in a browser
- Exporting the cookie file (see `cookie-extraction.md`)

The agent consumes the cookie via `--cookie-file` / `$BBC_COOKIE_FILE` /
`$BBC_SESSDATA` / auto-detect. It never invokes an auth retrieval path.

If cookie load fails **and stdin is not a TTY**, `bbc cookie-check` and
`bbc fetch` return `auth_required` immediately — they never block on an
interactive prompt.

## Safety tier

All commands are tier = **open** (read-only). Specifically:

- No commands mutate Bilibili state (no post/edit/delete)
- No commands write outside the user-chosen `--output` directory
- No subprocess shells out to user-supplied strings
- Cookie values are never logged to stdout/stderr; only cookie *names* may
  appear in `cookie-check` output

## Versioning

`schema_version` in every envelope signals breaking-change boundaries.
Minor version bumps add fields; major version bumps may rename or remove
fields. Agents that cache schema should compare versions on every run.
