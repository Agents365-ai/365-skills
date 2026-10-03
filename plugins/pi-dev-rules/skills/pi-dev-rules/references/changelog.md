# Pi: Changelog

Source: `packages/coding-agent/CHANGELOG.md` at pi@a7229ddc2. Built locally from the repository changelog; no network access.

A reverse-chronological release list, newest first. The highlight column is the first
bullet of each release's `### New Features` section, or its first bullet when that
section is absent, truncated to fit the table.

---

**Cadence**: Pi ships releases every 1–3 days. Run `bash scripts/refresh.sh` from a Pi
checkout to rebuild this file and the reference bundles.

## Recent releases

| Version | Date | Highlights |
| --------- | ------ | ----------- |
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
| **0.81.1** | 2026-07-21 | Verifiable release source archives — GitHub releases now include deterministic, checksummed source archives with instructions for rebuilding standa... |
| **0.81.0** | 2026-07-21 | Local llama.cpp model management — Connect to a llama.cpp router, search and download Hugging Face models, and explicitly load or unload models wit... |
| **0.80.10** | 2026-07-16 | Kimi Coding thinking compatibility — Kimi Coding models now use adaptive thinking correctly; K3 exposes its supported max level and supports replay... |
| **0.80.9** | 2026-07-16 | Kimi K3 and deferred tool loading — Use Kimi K3 across built-in providers, including progressive extension tool activation through Kimi’s native pr... |
| **0.80.8** | 2026-07-16 | Unified model runtime and provider authentication — ModelRuntime centralizes model configuration, provider-owned /login, and dynamic provider catal... |
| **0.80.7** | 2026-07-14 | Cache-friendly dynamic tool loading - Extensions can add tools during execution while supported Anthropic and OpenAI Responses models preserve prom... |

---

## Full changelog

283 release sections are recorded in the Pi repository, including `[Unreleased]`.
Read the complete, untruncated history there:

```bash
less "$PI_REPO/packages/coding-agent/CHANGELOG.md"   # PI_REPO is the pi checkout root
```
