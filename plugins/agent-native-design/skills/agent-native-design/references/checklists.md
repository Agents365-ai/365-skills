# Review Checklists

Use this when evaluating a CLI for agent readiness, or when sanity-checking a new design before shipping.

## Output

- [ ] `stdout` is valid JSON when stdout is not a TTY or when `--format json` is passed (success and failure)
- [ ] `stderr` carries human-readable diagnostics only
- [ ] JSON envelope is stable: `{ "ok": bool, "data": ... }` or `{ "ok": false, "error": ... }`
- [ ] Error object includes: `code`, `message`, `retryable`
- [ ] No prose mixed into `stdout`

## Exit codes

- [ ] Exit codes are documented
- [ ] Exit codes are stable across versions
- [ ] Distinct codes for: success (0), runtime error, auth error, validation error
- [ ] Exit code mapping is available via `--help` or `schema`

## Retry and interaction mode

- [ ] Every mutating command accepts `--idempotency-key`
- [ ] Retried calls with the same idempotency key return the original result
- [ ] `retryable` field in error envelope is meaningful and correct
- [ ] CLI never prompts for input when stdin is not a TTY
- [ ] `--yes` / `--no-input` / `--force` supported on every command that would otherwise prompt
- [ ] Returns structured `confirmation_required` error instead of blocking on missing confirmation
- [ ] stdout defaults to JSON when stdout is not a TTY (no `--format json` required)
- [ ] Pagers (`less`, `more`) disabled when stdout is not a TTY

## Self-description

- [ ] Top-level `--help` lists all resources/commands
- [ ] Resource-level `--help` lists actions
- [ ] Action-level `--help` lists all flags with types
- [ ] Schema introspection command available (`tool schema <resource.action>`)
- [ ] Dry-run available for all mutating commands

## Safety

- [ ] Read commands clearly discoverable
- [ ] Write/mutating commands carry explicit warning in help
- [ ] Destructive commands (delete/purge) hidden from skills or gated
- [ ] Dry-run covers all write operations

## Auth

- [ ] Human/system manages token acquisition (browser flow, keychain)
- [ ] Agent receives credential via env var or pre-fetched token
- [ ] Agent never navigates OAuth2 or browser flows
- [ ] Token refresh handled outside agent runtime

## Trust

- [ ] CLI args treated as untrusted (validated at boundary)
- [ ] Environment variables used for config/safety settings (human-set)
- [ ] Agent cannot escalate its own privileges via CLI args

## Schema

- [ ] Schema is the single source of truth
- [ ] CLI command structure derives from schema
- [ ] Validation derives from schema
- [ ] Help text derives from schema
- [ ] Generated skills derive from schema (if applicable)
- [ ] Schema version included in every response's `meta` block
- [ ] Deprecation signals included in schema responses (`deprecated_fields`, `replaced_by`, `removed_in`)
- [ ] Schema introspection is incremental (not eager): `--help` is small; full schema via `schema` subcommand only

## Token efficiency

For agents that call the CLI in loops (orchestration, multi-turn planning), context cost matters. These items help CLIs realize the per-call token advantage over eager-loaded MCP servers (see `hybrid-mcp-cli.md` for the benchmark data this is based on).

- [ ] Top-level `--help` response is under 500 tokens
- [ ] Full schema is not dumped in top-level `--help`; accessed via `schema <resource.action>` instead
- [ ] Field selection supported on list responses (`--json field1,field2,...` or similar)
- [ ] Default list responses are compact (3–5 fields); full detail via `--full` flag
- [ ] Requests that would normally require two CLI calls are collapsed (e.g., `count` + `list` → return count in the envelope)
- [ ] Schema versioning allows agents to cache and avoid re-discovery on every invocation
