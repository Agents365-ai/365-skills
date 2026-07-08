# Rubric

14 criteria, scored 0–2 each. Every criterion is tagged with the principle it backs, so scoring the rubric is the same act as auditing the seven principles. Use this when producing the score component of a CLI review.

| Criterion | Principle | 0 — Fail | 1 — Partial | 2 — Pass |
|-----------|-----------|----------|-------------|----------|
| **Three-audience support** | P0 | Designed for only one audience (human-only, or agent-only) | Serves two audiences well; the third is an afterthought or broken | Deliberately designed for human + agent + system with documented trade-offs |
| **Stdout contract** | P1 | Prose or mixed output | JSON sometimes, not always | Always parseable JSON with stable envelope when stdout is not a TTY (agent context); human-readable by default only under TTY or explicit `--format table` |
| **Stderr separation** | P1 | Diagnostics mixed into stdout | Some separation | Diagnostics always on stderr |
| **Exit code semantics** | P1/P2 | All errors map to same code | Some codes defined | Documented, stable, distinct codes per failure class |
| **Self-description (help)** | P3 | No `--help` or single flat page | Layered help exists but incomplete | Full progressive help: top → resource → action → schema |
| **Schema introspection** | P6 | Not available | Partial or undocumented | `tool schema <resource.action>` returns full typed schema |
| **Dry-run** | P3/P4 | Not available | Available for some commands | Available for all mutating commands |
| **Idempotent retries** | P1 | Mutating commands have no idempotency story; retries create duplicates | `--idempotency-key` exists on some commands, or retry semantics are inconsistent | Every mutating command accepts `--idempotency-key`; retried calls return the original result; the `retryable` flag in the error envelope is meaningful and correct |
| **Non-interactive operation** | P0 | CLI prompts on confirmation or password input regardless of TTY state; no `--yes`/`--force` flags | Some commands support `--yes` but TTY detection is incomplete or pagers still block | CLI never prompts when stdin is not a TTY; `--yes` / `--no-input` supported on every confirmation; pagers disabled when stdout is not a TTY; structured `confirmation_required` error returned instead of blocking |
| **Safety tiers** | P4 | Destructive ops at same level as reads | Some warning on destructive ops | Read/write/destructive clearly tiered; destructive hidden from skills |
| **Boundary validation** | P5 | Validation scattered across internal functions, or missing | Boundary validation exists but internal code still re-validates or accepts raw input | All input validated once at the CLI entry point; internal code operates on typed, trusted structures; validators are centralized and tested for pass and reject cases |
| **Auth delegation** | P7 | Agent manages token lifecycle, runs login or token-retrieval subcommands | Token via env var but refreshed by the agent | Human/system manages token acquisition and refresh; agent receives a pre-fetched credential and never invokes the auth retrieval path |
| **Error recoverability** | P1 | No error fields | `code` + `message` only | `code` + `message` + `retryable` + context fields |
| **Trust boundary** | P2 | CLI args used for auth/config | Mixed | Env vars / config set by human; agent supplies only runtime params |

**Scoring guide (max 28):**

- 26–28: Agent-native
- 17–25: Partially agent-native — specific gaps, actionable fixes
- 0–16: Not yet agent-native — structural redesign needed
