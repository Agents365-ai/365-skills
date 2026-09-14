# Pi: Changelog

Source: `packages/coding-agent/CHANGELOG.md` at pi@71dca871b. Built locally from the repository changelog; no network access.

A reverse-chronological release list, newest first. The highlight column is the first
bullet of each release's `### New Features` section, or its first bullet when that
section is absent, truncated to fit the table.

---

**Cadence**: Pi ships releases every 1–3 days. Run `bash scripts/refresh.sh` from a Pi
checkout to rebuild this file and the reference bundles.

## Recent releases

| Version | Date | Highlights |
| --------- | ------ | ----------- |
| Unreleased | unreleased | ctx.modelRegistry.stream() and streamSimple() for extension model calls through configured providers with resolved authentication (#8964). |
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
| **0.80.6** | 2026-07-09 | max thinking level - New opt-in thinking level above xhigh, natively supported on GPT-5.6 and adaptive Claude models, available across CLI (--think... |
| **0.80.5** | 2026-07-09 | (no notes recorded) |
| **0.80.4** | 2026-07-09 | Prompt cache miss visibility - Significant cache misses can be shown in transcripts via showCacheMissNotices. See Model & Thinking. |
| **0.80.3** | 2026-06-30 | Anthropic Claude Sonnet 5 support - Claude Sonnet 5 is available through inherited Anthropic-compatible and Bedrock provider catalogs with adaptive... |
| **0.80.2** | 2026-06-23 | inherited pi-ai ApiKeyCredential to use the auth.json-compatible discriminator type: "api_key" and provider-scoped env values instead of type: "api... |
| **0.80.1** | 2026-06-23 | inherited Amazon Bedrock scoped AWS_PROFILE endpoint resolution for built-in inference profile endpoints. |
| **0.80.0** | 2026-06-23 | Changed: Added Ctrl+J as a default newline keybinding alongside Shift+Enter. |
| **0.79.10** | 2026-06-22 | Extension compaction event context - Extension session_before_compact and session_compact events now include reason and willRetry, so extensions ca... |

---

## Full changelog

275 release sections are recorded in the Pi repository, including `[Unreleased]`.
Read the complete, untruncated history there:

```bash
less "$PI_REPO/packages/coding-agent/CHANGELOG.md"   # PI_REPO defaults to ~/github/pi
```
