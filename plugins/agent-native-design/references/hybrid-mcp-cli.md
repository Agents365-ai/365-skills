# When CLI vs MCP vs Both

This skill teaches CLI design — but the largest production agents (Claude Code, Cursor, Gemini CLI, CircleCI) use both CLI and MCP, not one or the other. This file is the single home for the CLI-vs-MCP discussion and the benchmark data behind it; SKILL.md and the checklists point here.

---

## The hybrid pattern

**State changes happen through the CLI. System understanding happens through MCP.**

- **Use CLI for:** local/scriptable tasks, composable automation, state-changing operations, dev/infrastructure workflows
- **Use MCP for:** multi-tenant SaaS, per-user authentication, stateful workflows, audit logs, fine-grained access control
- **Use both:** most production agents that orchestrate infrastructure (Vercel CLI + MCP for SaaS integrations; GitHub CLI + MCP for enterprise GitHub instances)

---

## Decision matrix

| Scenario | CLI | MCP | Notes |
|----------|-----|-----|-------|
| Single-user dev tool on same machine | ✅ | | Process model is cheap; auth is local; composable with Unix pipes |
| Large multi-tenant SaaS with per-user OAuth | | ✅ | Centralized auth; per-user scoping; network-attachable; no binary shipping required |
| Hundreds of tools where schema size matters | ✅ | ⚠️ | CLI wins: eager MCP schema dumps consume 55K–80K tokens upfront. CLI lazy-loads via progressive help. |
| Orchestration + infrastructure changes | ✅ | | State changes favor process-model CLIs |
| Complex permission models, audit requirements | | ✅ | MCP's structured audit logs and per-user attribution |
| Hybrid: local infra + cloud SaaS | ✅✅ | ✅ | CLI for infrastructure, MCP for SaaS. Both in same agent. |

---

## Benchmark data

These are the numbers behind the "CLI is more efficient than eager-loaded MCP" claim. Cite this section when SKILL.md or the checklists need backing.

- **Task completion:** CLI-based agents achieve **28% higher task completion** vs. MCP-only agents with the same token budget (Reinhard 2026).
- **Token efficiency:** **33% advantage** measured by Token Efficiency Score (CLI: 202, MCP: 152).
- **Per-task overhead:** ~4,150 tokens (CLI) vs ~145,000 tokens (MCP) for an identical browser-automation task — a 35× reduction (Reinhard 2026).
- **Schema dump cost:** MCP servers that load all tool schemas upfront consume **55K–80K tokens** just for discovery. An agent running 10 sequential operations sees this overhead on every orchestration handoff.
- **Lazy-loading wins, in either world:** Anthropic's *Code execution with MCP* (Nov 2025) reports that presenting MCP tools as code on a filesystem reduced one Google-Drive→Salesforce workflow from 150,000 tokens to 2,000 — a 98.7% saving. The same logic produces CLI's structural advantage: progressive `--help` is lazy-loading by default.

These numbers are why a CLI's progressive `--help` → resource help → `schema <resource.action>` pattern matters: the agent only pays for the parts it queries, not for everything the tool could do.

---

## When to stick with CLI alone

Mario Zechner's empirical benchmark (Aug 2025) of MCP vs CLI for coding agents lands on a one-line conclusion that's worth taking seriously: *"Just like a lot of meetings could have been emails, a lot of MCPs could have been CLI invocations."* That doesn't make MCP wrong; it means the default has been wrong. For the workflows this skill targets — developer tools, infrastructure CLIs, single-user data and research workflows — CLI is the lighter, more inspectable, more composable choice.

## When to switch to MCP or hybrid

If you reach a design where you'd be fighting the CLI process model (per-request user context, fine-grained per-call authorization, network-attached without local install, multi-tenant data isolation), that's the signal to add MCP to the mix, not to bend this skill out of shape. Consult the decision matrix above; if you need features from the MCP column, embrace the hybrid approach that production agents use.
