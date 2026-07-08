# Citations

Sources actually quoted or directly relied on in SKILL.md and the other reference files. The broader landscape (clig.dev, the gh / aws / kubectl design corpus) is implicit background.

## Anthropic engineering

- *Code execution with MCP: Building more efficient agents* — https://www.anthropic.com/engineering/code-execution-with-mcp (Nov 4, 2025). Progressive disclosure of tool definitions; the 150K → 2K token reduction case study cited under Principle 3 / `design-patterns.md#help-design`.
- *Beyond permission prompts: making Claude Code more secure and autonomous* — https://www.anthropic.com/engineering/claude-code-sandboxing (Oct 20, 2025). Approval fatigue and the 84% prompt-reduction figure cited under Principle 4 / `design-patterns.md#safety-design`.

## CLI-for-agents writing

- Ugo Enyioha, *Writing CLI Tools That AI Agents Actually Want to Use* — https://dev.to/uenyioha/writing-cli-tools-that-ai-agents-actually-want-to-use-39no (Feb 27, 2025). Idempotency-on-retry and "agents cannot type 'y'" framings cited in the Idempotency and Non-interactive sections of `design-patterns.md`.
- Thibault Le Ouay Ducasse / openstatus, *Building a CLI That Works for Humans and Machines* — https://www.openstatus.dev/blog/building-cli-for-human-and-agents (Apr 2, 2026). TTY detection as the human/machine switch cited under Principle 1.
- Mario Zechner, *MCP vs CLI: Benchmarking Tools for Coding Agents* — https://mariozechner.at/posts/2025-08-15-mcp-vs-cli/ (Aug 15, 2025). Empirical case that many MCP servers could be CLI invocations.
- Armin Ronacher, *Skills vs Dynamic MCP Loadouts* — https://lucumr.pocoo.org/2025/12/13/skills-vs-mcp/ (Dec 13, 2025). Schema/API stability as a first-class concern cited under Principle 6.

## CLI-vs-MCP benchmarks (2026)

- Jannik Reinhard, *CLI Tools vs MCP: Better AI Agents With Less Context* — https://jannikreinhard.com/2026/02/22/why-cli-tools-are-beating-mcp-for-ai-agents/ (Feb 22, 2026). Source for the 28% / 33% / 55K / 35× numbers in `hybrid-mcp-cli.md`.
- Manveer Chawla, *MCP vs. CLI for AI agents: When to Use Each (A Practical Decision Framework for 2026)* — https://manveerc.substack.com/p/mcp-vs-cli-ai-agents (Mar 8, 2026). Per-integration decision framework; production examples (Claude Code, Cowork) using both transports.
- Soumyadeb Mitra / RudderStack, *CLI or MCP or both? The design pattern for AI agents managing your data stack* — https://www.rudderstack.com/blog/ai-agents-cli-mcp-design-pattern/ (Mar 18, 2026). The "writes via CLI, reads via MCP" split underpinning `hybrid-mcp-cli.md`.

## Pre-agent baseline

- *Scripting with GitHub CLI* — https://github.blog/engineering/engineering-principles/scripting-with-github-cli/ (Mar 11, 2021). `gh api --jq` and structured JSON output as a first-class CLI pattern. The post predates the `gh <resource> --json field1,field2` field-selection flag (cli/cli#1089) but lays out the design philosophy that flag is built on.
- *Command Line Interface Guidelines* — https://clig.dev/. The pre-agent baseline for human-first CLI design. This skill extends it; it does not replace it.
- `sysexits.h` — https://manpages.ubuntu.com/manpages/noble/man3/sysexits.h.3head.html. The BSD exit-code vocabulary that `design-patterns.md#exit-code-model` deliberately simplifies away from.

---

## A note on the "agent-native CLI" framing

The term used throughout this skill is one of several competing framings in current writing. *Agent-first CLI* (Propel, Keyboards Down) is more common; *CLI for humans and machines* (openstatus, Linearis) is the most descriptive. "Native" is chosen here to emphasize that agent support is a first-class design goal, not a retrofit on top of a human-only CLI.
