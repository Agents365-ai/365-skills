# Pi: Changelog

Source: `packages/coding-agent/CHANGELOG.md` at pi@71023aec1. Built locally from the repository changelog; no network access.

A reverse-chronological release list, newest first. The highlight column is the first
bullet of each release's `### New Features` section, or its first bullet when that
section is absent, truncated to fit the table.

---

**Cadence**: Pi ships releases every 1–3 days. Run `bash scripts/refresh.sh` from a Pi
checkout to rebuild this file and the reference bundles.

## Recent releases

| Version | Date | Highlights |
| --------- | ------ | ----------- |
| **1.3.0** | 2026-10-15 | Choose where /share uploads: sessionShareDestination selects auto, gist, or radius. See Sessions and context and Export or share a session. |
| **1.2.0** | 2026-10-12 | Per-key OpenRouter model lists: with an OpenRouter key, Pi lists only the models that key may use, with the key's context size, max output, and pri... |
| **1.1.0** | 2026-10-07 | Program status reporting: terminals and agent dashboards that support OSC 7501 see whether Pi is working, blocked on a dialog or login, done, or fa... |
| **1.0.4** | 2026-10-05 | Tool patterns and --no-mcp: --tools and --exclude-tools accept * patterns, for example --tools read,codemode,'mcp__radius__*' keeps only one MCP se... |
| **1.0.3** | 2026-10-05 | Azure Foundry Chat Completions — The azure provider (renamed from azure-openai-responses) now also serves Foundry Chat Completions deployments, sta... |
| **1.0.2** | 2026-10-04 | Sampling by thinking level — samplingParamsByThinkingLevel in models.json sets sampling parameters such as temperature and top_p for each thinking... |
| **1.0.1** | 2026-10-03 | Nix flake — nix run github:earendil-works/pi/stable runs the latest release, and nix profile add github:earendil-works/pi/stable installs it. See I... |
| **1.0.0** | 2026-10-01 | Fullscreen by default — The TUI now runs fullscreen. Set tuiMode to "regular" to keep the terminal's normal scrollback. See Terminal and display. |
| **0.99.2** | 2026-09-30 | MCP servers stay out of the way: servers with the default codemode exposure are no longer listed in the codemode description and no longer block th... |
| **0.99.1** | 2026-09-29 | GPT-6.1 Sol — Available on OpenAI, Azure OpenAI, and OpenAI Codex, and now the default OpenAI Codex model. See Select a model. |
| **0.99.0** | 2026-09-29 | Codemode and MCP — Connect MCP servers and let models run JavaScript that calls tools in parallel. See MCP Servers and Enable codemode. |
| **0.87.1** | 2026-09-22 | Latest frontier models — Use Claude Opus 5.5, GPT-6 Sol, and GPT-6 Luna through supported providers, including GitHub Copilot. See Choose a Model. |
| **0.87.0** | 2026-09-21 | Canonical session context and extension boundaries — Edit model context without rewriting history and add actionable lifecycle hooks. See ContextEd... |
| **0.86.1** | 2026-09-20 | Meta Muse provider — Sign in with Meta using /login meta or use META_API_KEY to access Muse Spark models. See Meta (Muse subscription). |
| **0.86.0** | 2026-09-19 | Prompt cache warming — Keep valuable prompt caches alive during long tool runs and optionally while idle using cost-aware refreshes. See Cache Warm... |
| **0.85.1** | 2026-09-05 | GPT-6 Astra — Available through OpenAI API keys and OpenAI Codex subscriptions. See API Keys and OpenAI Codex. |
| **0.85.0** | 2026-09-04 | Persistent Claude thinking effort — Supported Anthropic transports preserve per-turn effort and recover safely from signed-thinking mismatches. See... |
| **0.84.4** | 2026-08-28 | Terminal capability overrides — Override detected terminal hyperlink, image, and truecolor support. See Capability Overrides. |
| **0.84.3** | 2026-08-24 | PowerShell tool — Use optional native PowerShell command execution on Windows. See PowerShell Tool. |
| **0.84.2** | 2026-08-14 | Fullscreen transcript search — Search and navigate matches in fullscreen mode. See TUI Fullscreen Viewport. |
| **0.84.1** | 2026-08-07 | Qwen Token Plan Individual — Use the built-in provider for models documented for Individual subscriptions. See API Keys. |
| **0.84.0** | 2026-08-06 | Fullscreen TUI mode — Switch between regular and fullscreen modes at runtime, with a sticky editor and footer, independently scrollable transcript,... |
| **0.83.0** | 2026-07-29 | Credential export for external clients — pi auth print-api-key and pi auth print-bearer-token export configured credentials with automatic OAuth re... |
| **0.82.1** | 2026-07-25 | Claude Opus 5 — Available on Anthropic and Amazon Bedrock with adaptive thinking (including xhigh), inference profiles, and prompt caching. See Pro... |
| **0.82.0** | 2026-07-24 | Constrained tool sampling — Tools can prefer or require strict JSON Schema sampling or use OpenAI Lark/regex grammars, with model capability metada... |

---

## Full changelog

289 release sections are recorded in the Pi repository, including `[Unreleased]`.
Read the complete, untruncated history there:

```bash
less "$PI_REPO/packages/coding-agent/CHANGELOG.md"   # PI_REPO is the pi checkout root
```
