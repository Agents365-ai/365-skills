# Changelog

[← Back to README](../README.md)

## v1.4.0 — September 1, 2026

**Machine verification baseline + new citations.**

- Added an `anc audit --output json` machine verification baseline to Step 4 of the standard review workflow: when the CLI under review is installed, the [agentnative](https://github.com/brettdavies/agentnative) linter probes shipped-binary behavior (non-interactive operation, JSON validity, help/version, exit codes, NO_COLOR, dry-run) before the 14-criterion rubric is applied. Rubric-only dimensions (trust directionality, boundary validation, safety tiers, auth delegation, schema version drift) remain agent-scored.
- Added Cloudflare's *The CLI for all of Cloudflare* (Apr 2026) to `references/citations.md` as independent industrial corroboration of the token-efficiency numbers in `hybrid-mcp-cli.md` and of Principle 6's schema-as-source-of-truth.
- Removed stale v1.3.3-era top-level copies (SKILL.md, references, docs, agents, scripts, READMEs) from the `365-skills` marketplace plugin directory; the synced `skills/agent-native-design/` copy is now the only one, matching the layout every other plugin in the marketplace uses.
- Relicensed from CC BY-NC 4.0 back to MIT: replaced the LICENSE file, set `license: MIT` in SKILL.md frontmatter, and updated both READMEs.
- Removed the Multi-Platform Support and Comparison (with vs. without this skill) tables from both READMEs; per-platform install detail stays in `docs/install.md` / `docs/install_CN.md`.
- Bumped version in SKILL.md frontmatter metadata to `1.4.0`.

## v1.3.5 — July 9, 2026

**Repo restructure for multi-skill workspace compatibility.**

- Moved SKILL.md, references, agents, and scripts into `skills/agent-native-design/` subdirectory so the repo can host multiple skills (compatible with the `365-skills` marketplace sync layout).
- Added GitHub Actions workflow to sync `skills/agent-native-design/` into the `Agents365-ai/365-skills` marketplace repo on push to main.
- Updated install docs: manual `git clone` installs now clone to `/tmp` then `cp -r skills/agent-native-design` into the target skills directory (marketplace installs unaffected).
- Fixed stale internal references (`examples.md` → `references/examples.md`) across SKILL.md and design-patterns.md.
- Bumped version in SKILL.md frontmatter metadata to `1.3.5`.
- Switched license from MIT to CC BY-NC 4.0.

## v1.3.4 — June 18, 2026

**Removed the in-skill update check (Step 0).**

Claude Code's plugin marketplace and SkillsMP now track skill versions and surface upgrade prompts, so the notify-only Step 0 added in v1.3.2 / reworked in v1.3.3 is no longer load-bearing — it was dead weight loaded into context on every conversation. The update lifecycle now belongs entirely to the install channel (`/plugin update`, or `git pull` for direct clones, documented in the README).

- Dropped `Step 0. Update check` from the standard review workflow in `SKILL.md`; the workflow now begins at Step 1.
- Removed the orphaned `.last_update` throttle file.
- Consistent with this skill's own *Principle 7* (the human/system owns the update lifecycle, not the agent) and closes the supply-chain surface a self-pull would reopen.

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
- Added 4 new references: Reinhard, Chawla, RudderStack on hybrid patterns (2026)
- Validated all 7 principles through April 2026 production deployments

**Recommendation:** This version reflects the consensus that large production agents (Claude Code, Cursor, Gemini CLI) use both CLI (for local/scriptable tasks) and MCP (for multi-tenant SaaS). Skill remains fundamentally sound; no principles required rewriting.

## v1.1.0 — Early 2026

Initial version with seven principles, 14-criterion rubric, and examples.
