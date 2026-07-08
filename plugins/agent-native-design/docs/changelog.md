# Changelog

[← Back to README](../README.md)

## v1.3.3 — May 5, 2026

**Replaced Step 0 silent auto-pull with a notify-only update check.**

On review, the v1.3.2 silent `git pull` proved inconsistent with this skill's own *Principle 2 (trust is directional)* and *Principle 7 (auth/lifecycle is delegated to the human, not owned by the agent)*. The new Step 0:

- **Throttles to one check per 24 h per installation** (was: every fresh conversation)
- **Notifies and asks** — surfaces the actual version delta (`vX.Y.Z → vA.B.C`) and pulls only with explicit user consent
- Same silent fallback for non-git-checkout installs (ClawHub copy, read-only paths)
- Removes the supply-chain attack surface where a compromised upstream could be silently fetched into every installation on the next conversation

If you upgraded to v1.3.2, this is the right reason to upgrade once more.

## v1.3.2 — May 5, 2026

**Auto-update step.** Added `Step 0` to the standard review workflow: on first use per conversation, the model checks `.last_update` and runs `git pull --ff-only` if older than 24 h, silently. Failure modes (offline, conflict, not a git checkout — e.g. ClawHub-installed copy) are ignored. Frees git-clone users from depending on whether the host runtime auto-pulls skills, and works identically across Claude Code / OpenClaw / Hermes / pi-mono / Codex.

## v1.3.1 — May 5, 2026

**Content depth + visual identity.**

- New `references/testing.md` (~235 lines): for every design pattern in `references/design-patterns.md`, a corresponding test recipe — envelope contracts, stdout/stderr separation, exit codes, idempotency replay, TTY behavior, schema drift, dry-run safety, auth delegation, locale determinism, streaming. Closes the "skill teaches how to design but not how to verify" gap.
- Bilingual concept hero image (`docs/assets/concept-hero-{en,zh}.png`) embedded in both READMEs and both landing pages — one visual carrying the "one CLI · three audiences · three channels" mental model.
- Title cleanup in both READMEs (dropped doubled "design", redundant "Skill" suffix, and the redundant repo-name prefix); landing pages re-synced to current name and version.
- `.claude/` is now gitignored.

## v1.3.0 — May 5, 2026

**Structural cleanup** — same content, leaner SKILL.md, on-demand reference loading.

- Split SKILL.md (919 → 237 lines) into a lean core plus `references/` (examples, rubric, checklists, design patterns, hybrid CLI/MCP discussion, citations). Reference files load only when needed, mirroring the progressive-disclosure pattern this skill teaches.
- Deduplicated overlapping discussion: hybrid CLI+MCP and schema versioning each have one detailed home now, with brief pointers elsewhere.
- Verified all citations against their primary sources; corrected two metadata errors (Manveer Chawla, not "Chugh"; Ugo Enyioha's piece is Feb 2025, not Feb 2026).
- Moved one-time review artifacts (`REVIEW_2026.md`, `IMPROVEMENTS_APPLIED.md`) into `docs/maintainers/` so they no longer appear at the repo root.

## [v1.2.0](https://github.com/Agents365-ai/agent-native-design/releases/tag/v1.2.0) — April 26, 2026

**2026 Research Update** — Aligned with latest agent-CLI design patterns and benchmarks.

**New Content:**
- Added hybrid MCP-CLI decision framework with decision matrix (3 scenarios for each pattern)
- Strengthened Principle 6 with schema versioning in response envelopes and deprecation signals
- Added Example 8: Schema versioning with drift detection for agent caching scenarios
- Quantified anti-pattern: eager schema dumps (55K tokens per 10 invocations)
- Added token efficiency checklist (6 items for evaluating CLI context cost)

**Research Alignment:**
- Cite 2026 benchmarks: CLI achieves 28% higher task completion, 33% token efficiency vs. MCP-only
- Added 4 new references: Reinhardt, Chugh, RudderStack on hybrid patterns (2026)
- Validated all 7 principles through April 2026 production deployments

**Recommendation:** This version reflects the consensus that large production agents (Claude Code, Cursor, Gemini CLI) use both CLI (for local/scriptable tasks) and MCP (for multi-tenant SaaS). Skill remains fundamentally sound; no principles required rewriting.

## v1.1.0 — Early 2026

Initial version with seven principles, 14-criterion rubric, and examples.
