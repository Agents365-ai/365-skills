---
name: agent-native-design
description: Use when designing, reviewing, or refactoring a CLI that must serve AI agents alongside humans, or when converting an API or SDK into an agent-usable CLI interface.
license: MIT
homepage: https://github.com/Agents365-ai/agent-native-design
compatibility: Includes sidecar metadata for OpenClaw, Hermes, pi-mono, and OpenAI Codex; the core SKILL.md is portable to any agent runtime that supports Agent Skills-style instructions.
platforms: [macos, linux, windows]
metadata: {"openclaw":{"requires":{},"emoji":"⌨️","os":["darwin","linux","win32"]},"hermes":{"tags":["cli","agent-native","interface-design","structured-output","schema-driven"],"category":"engineering","requires_tools":[],"related_skills":[]},"pimo":{"category":"engineering","tags":["cli","agent-native","interface-design","structured-output","schema-driven"]},"author":"Agents365-ai","version":"1.3.4"}
---

# agent-native-design

## Purpose

This skill helps analyze, design, and refactor command-line tools so they can reliably serve **humans**, **AI agents**, and **orchestration systems** at the same time.

It is not a skill for merely *using* a CLI. It is a skill for designing and reviewing a CLI as an **agent-native interface**.

The skill focuses on four goals:

1. Make CLI behavior predictable for AI agents.
2. Make CLI output readable and recoverable for humans.
3. Make CLI execution manageable for systems and orchestrators.
4. Define a complete interaction loop from authentication to error routing.

---

## When to use this skill

Use this skill when the user wants to:

* evaluate whether an existing CLI is agent-friendly
* redesign a CLI to better support AI agents
* convert an API or SDK into an agent-native CLI
* review help output, schema design, exit codes, or JSON contracts
* design dry-run, auth delegation, or safety boundaries
* generate CLI skills, docs, or interface conventions from schema
* refactor a human-oriented CLI into a machine-friendly one
* define how a CLI should interact with an agent runtime

Typical prompts include:

* "Review this CLI and tell me whether it is agent-native."
* "Design a CLI for this API that an AI agent can use reliably."
* "Refactor this tool so stdout is machine-readable and safer for agents."
* "Help me define schema introspection, dry-run, and exit code semantics."

## When not to use this skill

Do not use this skill when the user only wants:

* help running a specific command
* installation help for a CLI
* shell troubleshooting unrelated to interface design
* generic Linux or terminal tutorials
* agent planning or memory design unrelated to tools
* API business logic review without any CLI/tooling layer

---

## Core model

An agent-native CLI must simultaneously serve three audiences.

### 1. Human

Needs: readable output, friendly error messages, onboarding guidance.
Channels: `stderr`, optional `--format table`, interactive TUI when appropriate.

### 2. AI Agent

Needs: structured data, stable contracts, self-description.
Channels: `stdout` as JSON, stable exit codes, schema introspection, dry-run previews, generated skills/docs.

### 3. System / Orchestrator

Needs: delegated authentication, process management, deterministic error routing.
Channels: environment variables, exit codes, dry-run mode, stable command semantics.

### Foundational contract

| Channel | Primary audience |
|---------|-----------------|
| `stdout` | Machines and agents |
| `stderr` | Humans |
| `exit codes` | Systems and orchestrators |

This skill teaches how to make CLI a first-class interface for agents. Production agents (Claude Code, Cursor, Gemini CLI) often pair a CLI with an MCP server — CLI for state changes and local/scriptable work, MCP for multi-tenant SaaS and per-user auth. When a design needs the MCP side as well, see `references/hybrid-mcp-cli.md` for the decision matrix and the benchmark data behind the CLI/MCP tradeoff.

---

## The complete interaction loop

| Phase | Step | Description |
|-------|------|-------------|
| 0. Bootstrap | 1 | Human/system obtains auth token or credentials |
| 0. Bootstrap | 2 | Set trusted env vars: token, profile, safety mode |
| 1. Discovery | 3 | Agent loads skills or command summaries |
| 1. Discovery | 4 | Agent queries schema/help for parameters |
| 2. Planning | 5 | Agent uses `--dry-run` to preview request shape |
| 3. Execution | 6 | Agent executes with validated inputs |
| 4. Interpretation | 7 | Agent parses structured result |
| 5. Recovery | 8 | Agent uses exit code + error object to retry, re-auth, repair, or escalate |

A CLI that does not support every phase is incomplete from the agent's perspective.

---

## Seven principles

These are load-bearing. Each principle has at least one rubric criterion and at least one example backing it.

### Principle 0. One CLI, Three Audiences

The CLI must serve human, agent, and system simultaneously. A design that serves only one audience is incomplete.

### Principle 1. Structured Output Is the Interface

`stdout` should always be parseable and stable. Both success and failure are structured JSON. The CLI must decide for itself which audience is reading: detect at startup whether stdout is a TTY, default to JSON when it is not, default to human-readable when it is. `NO_COLOR` and an explicit `--format json|table` flag override the auto-detection. Agents should never have to remember to pass `--format json` — if they have to, they will forget, and the run will silently produce un-parseable prose. Envelope and error contract: `references/design-patterns.md#output-envelopes`.

### Principle 2. Trust Is Directional

CLI arguments are not inherently trusted — they may come from a hallucinating or prompt-injected agent. Environment-level configuration set by the human or system is more trusted. The agent chooses *what to do* within a bounded surface; the human defines *where and how it is allowed to operate*.

### Principle 3. The CLI Must Describe Itself

The CLI must be self-describing enough that an agent can use it without reading external README files. Self-description must be **progressive**, not eager: top-level `--help` lists resources; resource help lists actions; action help lists flags; a separate `schema <resource.action>` returns the full typed schema. A CLI with hundreds of commands that dumps everything into the first `--help` pays that token cost on every agent invocation. See `references/design-patterns.md#help-design` and `examples.md` Examples 2 and 5.

### Principle 4. Safety Through Graduated Visibility

Read commands are easy to discover; mutating commands carry explicit warnings; destructive commands are hidden from skills or gated separately. Tier table and rationale: `references/design-patterns.md#safety-design`. Tiers are necessary but not sufficient — they are a prompt-side defense and approval fatigue degrades them quickly. Assume the agent runtime will additionally sandbox the CLI at the OS level (filesystem, network, processes), and design destructive commands to fail closed inside that sandbox.

### Principle 5. Validate at the Boundary, Not in the Middle

Inputs are validated once at the CLI entry point. Internal code operates on validated, typed, trusted structures. Validation functions are centralized and tested for both pass and reject cases.

### Principle 6. The Schema Is the Source of Truth

If a schema exists, everything derives from it: CLI command structure, validation rules, help text, generated docs, generated skills, type definitions, dry-run contracts. The schema is never manually duplicated. The schema must also carry its own version and deprecation signals, surfaced in the `meta` block of every response, so agents that have cached an older view can detect drift and re-discover rather than silently calling a removed method. Full versioning contract and example: `references/design-patterns.md#schema-versioning`.

### Principle 7. Authentication Must Be Delegatable

Authentication is obtained and refreshed by human/system-managed flows. The agent uses credentials; it never owns the auth lifecycle. Preferred mechanisms: environment variables, config files, OS keychain integration, externally refreshed tokens. Canonical pattern: `examples.md` Example 3.

---

## Standard review workflow

### Step 1. Classify the input

Decide whether the user is providing: an existing CLI, an API to be wrapped, a conceptual design, a partial interface, or a failure case.

### Step 2. Map the three audiences

**Human:** Is there readable output? Are errors understandable? Is onboarding supported?

**Agent:** Is stdout stable JSON? Can the CLI describe itself? Is there schema introspection and dry-run?

**System:** Is auth delegatable? Are exit codes stable? Can failures be routed deterministically?

### Step 3. Review the interaction loop

Check whether the CLI supports: bootstrap, discovery, parameter understanding, preview, execution, parsing, recovery.

### Step 4. Score the CLI with the rubric, then map back to principles

Use the 14-criterion rubric to score the CLI. The full rubric lives in `references/rubric.md`. Every one of the seven principles has at least one rubric row backing it, so the score-to-principle mapping is total: P0 → Three-audience support, Non-interactive operation; P1 → Stdout contract, Stderr separation, Idempotent retries, Error recoverability; P2 → Trust boundary; P3 → Self-description (help), Dry-run; P4 → Safety tiers; P5 → Boundary validation; P6 → Schema introspection; P7 → Auth delegation. Then summarize per principle with evidence, risk, and recommendation. The full review checklists live in `references/checklists.md`.

### Step 5. Produce a refactor plan

- **P0** must fix
- **P1** should improve
- **P2** long-term enhancements

---

## Default output format

### 1. Overall verdict

State whether the CLI is **agent-native**, **partially agent-native**, or **not yet agent-native**.

### 2. Three-audience contract review

Assess support for human, agent, system.

### 3. Interaction loop coverage

Assess each phase: auth bootstrap → env setup → skill/help discovery → schema introspection → dry-run → execution → parsing and recovery.

### 4. Rubric score + seven-principle review

Report the 14-criterion rubric score first, then summarize the seven principles as: status · evidence · issue · recommendation.

### 5. Key risks

Summarize design failures: human-only output, unstable JSON, no schema introspection, destructive commands overexposed, auth coupled to agent, ambiguous exit codes.

### 6. Refactor plan

Prioritized recommendations with examples drawn from `references/examples.md`.

---

## Things this skill should avoid recommending

* Human-readable prose as the only output contract
* README required for basic command discovery
* Schema and validation that drift apart
* Auth supplied primarily via agent-generated arguments
* Destructive actions exposed by default
* CLI behavior that depends on undocumented conventions
* Errors that are only textual and not machine-routable
* Mutating commands that are not idempotent under retry
* Confirmation prompts with no `--yes` escape and no TTY-aware fallback
* Eager schema dumps in top-level `--help` — agents that call the CLI in loops pay this cost on every invocation; use progressive disclosure instead. The token-cost rationale lives in `references/hybrid-mcp-cli.md`.

---

## Reference files

Load on demand — these are not in the agent's context until needed:

| File | Read when |
|------|-----------|
| `references/examples.md` | Showing the user a good envelope, error, dry-run, batch response, or anti-pattern |
| `references/rubric.md` | Producing the score component of a CLI review |
| `references/checklists.md` | Walking through a CLI auditing list with the user, or sanity-checking a new design |
| `references/design-patterns.md` | Writing the contract for envelopes, exit codes, idempotency, non-interactive mode, long-running commands, schema versioning, locale/time |
| `references/hybrid-mcp-cli.md` | Deciding CLI vs. MCP vs. both, or citing benchmark numbers behind the CLI efficiency claim |
| `references/testing.md` | Showing the user how to verify their CLI actually upholds the contract (envelope shape, idempotency replay, TTY behavior, schema drift, dry-run safety, locale determinism) — load this when the design review converges on "how do we keep it agent-native over time?" |
| `references/citations.md` | Citing the primary sources behind a recommendation |

---

## One-sentence summary

This skill helps turn a CLI into a trustworthy execution interface for **humans, AI agents, and systems** through **structured output, self-description, delegated authentication, safety boundaries, and a complete interaction loop**.
