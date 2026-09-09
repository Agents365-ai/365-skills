# Pi — Changelog

Source: <https://pi.dev/news> · RSS: `https://pi.dev/news.xml`

A reverse-chronological release-notes feed. Fetched from the RSS feed.

---

**Cadence**: Pi ships releases every 1–3 days. Run `bash scripts/refresh.sh`
to refresh both the package catalog and this changelog.

## Recent releases

| Version | Date | Highlights |
| --------- | ------ | ----------- |
| **0.85.0** | 2026-09-04 | New Features: Persistent Claude thinking effort — Supported Anthropic transports preserve per-turn effort and recover sa |
| **0.84.4** | 2026-08-28 | New Features: Terminal capability overrides — Override detected terminal hyperlink, image, and truecolor support. See Ca |
| **0.84.3** | 2026-08-24 | New Features: PowerShell tool — Use optional native PowerShell command execution on Windows. See PowerShell Tool.; Break |
| **0.84.2** | 2026-08-14 | New Features: Fullscreen transcript search — Search and navigate matches in fullscreen mode. See TUI Fullscreen Viewport |
| **0.84.1** | 2026-08-07 | New Features: Qwen Token Plan Individual — Use the built-in provider for models documented for Individual subscriptions. |
| **0.84.0** | 2026-08-06 | New Features: Fullscreen TUI mode — Switch between regular and fullscreen modes at runtime, with a sticky editor and foo |
| **0.83.0** | 2026-07-29 | New Features: Credential export for external clients — pi auth print-api-key and pi auth print-bearer-token export confi |
| **0.82.1** | 2026-07-25 | New Features: Claude Opus 5 — Available on Anthropic and Amazon Bedrock with adaptive thinking (including xhigh), infere |
| **0.82.0** | 2026-07-24 | New Features: Constrained tool sampling — Tools can prefer or require strict JSON Schema sampling or use OpenAI Lark/reg |
| **0.81.1** | 2026-07-21 | New Features: Verifiable release source archives — GitHub releases now include deterministic, checksummed source archive |
| **0.81.0** | 2026-07-21 | New Features: Local llama.cpp model management — Connect to a llama.cpp router, search and download Hugging Face models, |
| **0.80.10** | 2026-07-16 | New Features: Kimi Coding thinking compatibility — Kimi Coding models now use adaptive thinking correctly; K3 exposes it |
| **0.80.9** | 2026-07-16 | New Features: Kimi K3 and deferred tool loading — Use Kimi K3 across built-in providers, including progressive extension |
| **0.80.8** | 2026-07-16 | New Features: Unified model runtime and provider authentication — ModelRuntime centralizes model configuration, provider |
| **0.80.7** | 2026-07-14 | Breaking Changes: Removed the openai-responses compat.sendSessionIdHeader flag from models.json. Session-affinity behavi |
| **0.80.6** | 2026-07-09 | New Features: max thinking level - New opt-in thinking level above xhigh, natively supported on GPT-5.6 and adaptive Cla |
| **0.80.4** | 2026-07-09 | New Features: Prompt cache miss visibility - Significant cache misses can be shown in transcripts via showCacheMissNotic |
| **0.80.3** | 2026-06-30 | New Features: Anthropic Claude Sonnet 5 support - Claude Sonnet 5 is available through inherited Anthropic-compatible an |
| **0.80.2** | 2026-06-23 | Changed: Changed inherited pi-ai ApiKeyCredential to use the auth.json-compatible discriminator type: "api_key" and prov |
| **0.80.1** | 2026-06-23 | Release notes for Pi 0.80.1. |

---

## Fetch live

```bash
curl -s 'https://pi.dev/news.xml'
```
