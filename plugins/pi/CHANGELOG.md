# Changelog

## 0.1.2

- Model-agnostic: removed hard-coded `deepseek-v4-flash` / `deepseek-v4-pro` defaults
  that caused spawn failures for non-DeepSeek users.
- New env-var overrides: `PI_PLUGIN_REVIEW_MODEL` and
  `PI_PLUGIN_ADVERSARIAL_REVIEW_MODEL`. With nothing set, the plugin defers
  model selection entirely to pi.
- README rewritten as model-agnostic with a per-provider suggested-model table.

## 0.1.1

- Fixed 14 findings from a dual pi+DeepSeek self-review (3 critical, 2 high,
  6 medium, 3 low). Highlights: close()/agent_end deadlock fixes, SIGKILL
  escalation, stop-review-gate no longer silently bypasses when pi is
  unavailable, bounded stderr buffer, StringDecoder flush on close.

## 0.1.0

- Initial release of the Pi plugin for Claude Code, forked from `codex-plugin-cc`.
