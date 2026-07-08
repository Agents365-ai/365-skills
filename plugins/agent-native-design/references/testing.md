# Testing an Agent-Native CLI

A CLI's "agent-native" claim is empirically falsifiable. Every contract this skill teaches — envelope shape, exit code semantics, idempotency, TTY behavior, dry-run safety, schema stability — is something an agent will discover at runtime. The cheaper, kinder discovery path is a CI suite that finds the breakage first.

This file mirrors `design-patterns.md` topic by topic. Each section: the rule, how to verify it, a minimal harness, and what a passing-into-broken regression looks like. Examples use bash because CLIs are language-agnostic and bash is the universal harness; the same checks port to `bats`, `pytest` + `subprocess`, or whatever your repo already has.

---

## Envelope contracts (P1, P6)

**Rule.** Every response on stdout is valid JSON in the documented envelope shape (`ok: true|false|"partial"`, `data` or `error`, optional `meta`).

**How to verify.** Parse stdout as JSON; validate against a JSON Schema kept in the repo; snapshot a representative success and failure per command.

```bash
# Smoke: every documented command must produce parseable JSON.
for cmd in $(tool _internal list-commands); do
  out=$(eval "$cmd --dry-run" 2>/dev/null) || true
  echo "$out" | jq -e 'has("ok")' > /dev/null \
    || { echo "FAIL: $cmd produced non-JSON or missing 'ok'"; exit 1; }
done

# Schema: validate each envelope against the published contract.
echo "$out" | jq . | ajv validate -s schemas/envelope.schema.json -d -
```

**Regression looks like:** a release that adds a new field at the top level instead of inside `data` or `meta`; a command that returns a bare array instead of an envelope; pretty-print whitespace creeping in and breaking byte-equal snapshots.

---

## Stdout/stderr separation (P1)

**Rule.** Stdout carries the JSON envelope only. Stderr carries human diagnostics or NDJSON progress events — never the final envelope.

**How to verify.** Capture both streams independently, then assert stdout parses as exactly one JSON document and stderr does not.

```bash
out=$(mktemp); err=$(mktemp)
tool sleep list --start-date 2026-01-01 --end-date 2026-01-07 >"$out" 2>"$err"

jq -e . "$out" > /dev/null || { echo "FAIL: stdout is not a single JSON doc"; exit 1; }
if jq -e 'has("ok")' "$err" 2>/dev/null; then
  echo "FAIL: envelope leaked into stderr"; exit 1
fi
```

**Regression looks like:** a `printf "fetching..."` left in by a refactor; a debug `console.log` going to stdout instead of stderr; progress text appearing inline with the result envelope.

---

## Exit code semantics (P1/P2)

**Rule.** Each failure class maps to a stable, documented exit code. Success is `0`; one code per failure family thereafter.

**How to verify.** Synthesize each failure class deliberately and assert the code. Keep the assertions parameterized so adding a new class is one line.

```bash
declare -A cases=(
  [success]="tool sleep list --start-date 2026-01-01 --end-date 2026-01-07|0"
  [validation]="tool sleep list --start-date not-a-date|3"
  [auth]="HEALTHKIT_TOKEN=invalid tool sleep list --start-date 2026-01-01 --end-date 2026-01-07|2"
  [runtime]="HEALTHKIT_BASE_URL=http://127.0.0.1:1 tool sleep list --start-date 2026-01-01 --end-date 2026-01-07|1"
)
for name in "${!cases[@]}"; do
  IFS='|' read -r cmd want <<< "${cases[$name]}"
  eval "$cmd" >/dev/null 2>&1; got=$?
  [[ "$got" == "$want" ]] || { echo "FAIL: $name expected $want, got $got"; exit 1; }
done
```

**Regression looks like:** a refactor that collapses validation and runtime errors into the same `1`; a try/catch that swallows the auth code and re-emits it as `1`.

---

## Idempotency replay (P1)

**Rule.** A mutating command invoked twice with the same `--idempotency-key` returns the same envelope, and the side effect happens only once.

**How to verify.** Run twice, diff the bytes, then check the backing store. Both must be identical / unchanged on the second call.

```bash
key="test-$(uuidgen)"
r1=$(tool alerts send --recipient u1 --message hi --idempotency-key "$key")
r2=$(tool alerts send --recipient u1 --message hi --idempotency-key "$key")

diff <(echo "$r1") <(echo "$r2") || { echo "FAIL: replay returned different envelope"; exit 1; }

count=$(tool _internal alert-rows-for-key "$key")
[[ "$count" == "1" ]] || { echo "FAIL: side-effect ran $count times, expected 1"; exit 1; }
```

**Regression looks like:** the second call returns a fresh `id` / `created_at`; a duplicate row appears in the audit table; the `next` slot in the original response no longer matches on replay.

---

## Non-interactive / TTY behavior (P0)

**Rule.** When stdin is not a TTY the CLI never prompts; when stdout is not a TTY it never invokes a pager. Confirmations return a structured `confirmation_required` error instead of blocking.

**How to verify.** Run under a closed stdin with a wall-clock timeout. The process must exit cleanly within the timeout and produce a structured envelope, not a hang.

```bash
# Stdin not a TTY: must not block.
out=$(echo | timeout 5 tool danger purge --id abc 2>&1)
got=$?
[[ "$got" != "124" ]] || { echo "FAIL: command hung (timed out)"; exit 1; }
echo "$out" | jq -e '.error.code == "confirmation_required"' > /dev/null \
  || { echo "FAIL: expected confirmation_required envelope, got: $out"; exit 1; }

# --yes path: same command must succeed without prompting.
echo | timeout 5 tool danger purge --id abc --yes >/dev/null \
  || { echo "FAIL: --yes did not bypass the prompt"; exit 1; }

# Stdout not a TTY: pager must not be invoked.
PAGER='/bin/false' tool sleep list --start-date 2026-01-01 --end-date 2026-01-07 \
  | jq -e . > /dev/null || { echo "FAIL: pager invoked under non-TTY stdout"; exit 1; }
```

**Regression looks like:** an interactive `read -p` slipped in for a new flag; a library upgrade that re-enables pager autodetect; a `Press Enter to continue` left in a long-running command.

---

## Self-description and schema drift (P3, P6)

**Rule.** `--help` is small enough to live in an agent's context (a few hundred tokens at the top, growing only as the agent narrows its target). The `schema` subcommand returns a typed contract that includes `schema_version`. Cached agents detect drift through the version, not by hitting a removed method.

**How to verify.** Snapshot help-output byte size as an upper bound; parse `schema <method>` and assert it includes the documented fields; on every release, diff the schema snapshot and fail loudly on incompatible changes.

```bash
# Token budget on top-level help (rough proxy: bytes / 4 ~ tokens).
limit=2000
size=$(tool --help | wc -c)
[[ "$size" -le "$limit" ]] || { echo "FAIL: top-level --help is $size bytes, limit $limit"; exit 1; }

# Schema endpoint is real and includes versioning.
tool schema sleep.list | jq -e '.schema_version and .params and .introduced_in' > /dev/null \
  || { echo "FAIL: schema response missing required fields"; exit 1; }

# Schema regression gate: snapshot diff blocks accidental breaking changes.
tool schema sleep.list > /tmp/schema.new.json
diff -u tests/snapshots/schema.sleep.list.json /tmp/schema.new.json \
  || { echo "REVIEW: schema changed — confirm version bump and deprecation signals"; exit 1; }
```

**Regression looks like:** a help generator that starts emitting the full schema in `--help`; a schema response that drops `schema_version` after a refactor; a field renamed between versions without a `deprecated` / `replaced_by` entry on the old name.

---

## Dry-run safety (P3, P4)

**Rule.** Every mutating command supports `--dry-run`. The dry-run output describes the would-be request. No side effect occurs.

**How to verify.** Drive every mutating command in dry-run mode, assert the envelope shape, then assert the backing store is unchanged.

```bash
before=$(tool _internal store-fingerprint)

for cmd in $(tool _internal list-mutating-commands); do
  out=$(eval "$cmd --dry-run" 2>&1)
  echo "$out" | jq -e '.dry_run == true and .would_request' > /dev/null \
    || { echo "FAIL: $cmd --dry-run is missing dry_run/would_request"; exit 1; }
done

after=$(tool _internal store-fingerprint)
[[ "$before" == "$after" ]] || { echo "FAIL: dry-run mutated state"; exit 1; }
```

**Regression looks like:** a new mutating command shipped without `--dry-run` wired up; a dry-run path that still issues the upstream request; an envelope that drops the `dry_run: true` flag.

---

## Auth delegation (P7)

**Rule.** The agent never invokes the auth lifecycle (`auth login`, `auth token`, browser flows). It receives a credential from a human-managed env var and consumes it.

**How to verify.** Grep the generated agent-facing artifacts (skills, MCP tool manifests, examples) for the auth subcommands. Any reference is a violation.

```bash
forbidden='auth login|auth token|auth refresh'
hits=$(grep -RInE "$forbidden" skills/ docs/ agents/ 2>/dev/null | grep -v '^//' || true)
[[ -z "$hits" ]] || { echo "FAIL: agent surface references auth lifecycle:"; echo "$hits"; exit 1; }
```

**Regression looks like:** a worked example in the skill that pipes `auth token` into the next command; a generated MCP tool that exposes `auth.login`; an "easy onboarding" addition that has the agent call `auth login` itself.

---

## Locale and time determinism

**Rule.** Output bytes are identical regardless of host locale or timezone. Timestamps are UTC ISO-8601, dates are ISO-8601, numbers use `.` and no thousands separator.

**How to verify.** Run the same invocation under two divergent locales and one shifted timezone. The captured bytes must match exactly.

```bash
fixed=(--start-date 2026-01-01 --end-date 2026-01-07)

a=$(LC_ALL=C       TZ=UTC          tool sleep list "${fixed[@]}")
b=$(LC_ALL=de_DE.UTF-8 TZ=Asia/Tokyo tool sleep list "${fixed[@]}")

diff <(echo "$a") <(echo "$b") || { echo "FAIL: output drifted with locale/TZ"; exit 1; }
```

**Regression looks like:** `1.234,56` appearing instead of `1234.56`; a timestamp printed as `Mo., 12. Jan. 2026` instead of `2026-01-12T00:00:00Z`; a sort order that rearranges itself when the host's `LANG` changes.

---

## Long-running output and streaming

**Rule.** Long-running commands emit structured progress on stderr (one JSON object per line) and a single envelope on stdout. NDJSON list commands emit one envelope per line plus a final summary.

**How to verify.** Run with stderr redirected to a file, assert each line parses as JSON with an `event` field; for `--stream`, assert the last line carries a `summary`.

```bash
tool export run --dataset sleep --since 2024-01-01 > /tmp/result.json 2> /tmp/progress.log
jq -e . /tmp/result.json > /dev/null || { echo "FAIL: stdout not a single envelope"; exit 1; }
while IFS= read -r line; do
  echo "$line" | jq -e 'has("event")' > /dev/null \
    || { echo "FAIL: stderr line is not structured: $line"; exit 1; }
done < /tmp/progress.log

tool sleep list --since 2024-01-01 --stream | tail -1 \
  | jq -e '.summary' > /dev/null || { echo "FAIL: stream missing final summary"; exit 1; }
```

**Regression looks like:** progress events going to stdout and breaking the redirect-to-file pattern; an extra blank line at the end of `--stream` that breaks `tail -1`; a refactor that turns the per-line JSON into a single big array at the end.

---

## Wiring it into CI

These checks are cheap — most are seconds — and they belong on every PR. Three things make them durable:

1. **Treat the schema snapshot like a public ABI.** A diff is a release decision, not a code-review nitpick. Pair it with a CHANGELOG entry and a version bump.
2. **Run the locale and TTY tests in their own job.** They depend on environment shape, not on the build, and they fail fast when a maintainer's local laptop is the only thing the CLI was ever tested under.
3. **Keep the failure messages structured.** A test suite for an agent-native CLI is itself an agent surface — the messages above are written so an LLM driving CI can read them and route the fix without grepping logs.
