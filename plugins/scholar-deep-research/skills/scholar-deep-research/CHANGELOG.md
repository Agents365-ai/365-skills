# Changelog

Notable changes to `scholar-deep-research`. Format follows
[Keep a Changelog](https://keepachangelog.com); fragments are managed by
[towncrier](https://towncrier.readthedocs.io) — see `changelog.d/README.md`.

<!-- towncrier release notes start -->

## 0.16.2 — 2026-05-12

### Bug fixes

- Three call sites (`extract_pdf.py --url`, `_pdf_fetch.py` Unpaywall
  API and PDF download) hardcoded `User-Agent:
  scholar-deep-research/0.1` — a stale version string from the
  pre-0.5 era. Replaced with the canonical `USER_AGENT` from
  `_common.py`, which already carries the live version + repo URL +
  polite-pool marker. The honest-bot identity is more likely to pass
  publisher UA filters than a bare `name/version` token, and the
  single source of truth means future version bumps don't leave the
  fetch headers behind. Caught while diagnosing why paper-fetch
  failed on GraphDTA — paper-fetch's own UA filtering bug is filed
  separately upstream.


## 0.16.1 — 2026-05-12

### Features

- arXiv 429 cooldown is now honored across processes. The per-source
  rate limiter's lock-file semantics changed from "last-call
  timestamp" to "earliest-next-call time", and a new
  `note_rate_limit_cooldown(source, retry_after_seconds)` helper lets
  search scripts push that gate forward when an upstream returns 429.
  `search_arxiv.py` calls it with `Retry-After` header (when present)
  or 90s default — sibling processes that share `SCHOLAR_CACHE_DIR`
  will now wait out arXiv's sticky penalty box instead of each
  hitting the wall in turn. Existing 0.15.x lock files auto-migrate
  on first write; tests cover cooldown wait, no-op on
  zero/negative, and never-pulls-gate-backward semantics.


## 0.16.0 — 2026-05-12

### Bug fixes

- `SCHOLAR_SATURATION_NEW_PCT` default bumped from 20.0 → 50.0 on
  the paper axis. The 0.13.x threshold was unreachable against real
  broad-topic corpora — the v0.15.1 end-to-end DTI validation needed
  2 rounds against 3 sources to advance G2 and still saw 78–93% new
  in round 2, far above 20%. Operators who want systematic-review
  rigor can pin `SCHOLAR_SATURATION_NEW_PCT=20` in their env. The
  author/venue thresholds (25%/30%) are unchanged — they had
  different conceptual headroom.


## 0.15.2 — 2026-05-12

### Bug fixes

- Fix contract bug in `references/agent_prompts/phase3_deep_read.md`
  step (d): the v0.15.1 instruction recorded WebFetch landing-page
  evidence with `depth: "abstract_only"`, but the `evidence` CLI only
  accepts `full` / `shallow` and would return `invalid_field`. The
  prompt now uses `--depth shallow` with a `webfetch_landing_page:`
  method prefix — the same prefix convention as failure modes A
  (`evidence_unavailable:`) and B (`topic_mismatch:`). No code
  changes; this is a docs/prompt fix only. Caught by the v0.15.1
  end-to-end validation run.


## 0.15.1 — 2026-05-12

### Documentation

- SKILL.md now documents host-native web tool enrichment alongside the
  existing MCP enrichment section, covering Claude Code (`WebSearch` /
  `WebFetch`), OpenCode (`webfetch`), Codex CLI, and the
  OpenClaw/Hermes/pi-mono/Manus pattern (route through configured MCP).
  Phase 3 deep-read prompt gains a step (d) — WebFetch the paper's
  landing page as the last resort before writing
  `evidence_unavailable`, with `depth: "abstract_only"` to flag partial
  coverage. Pure documentation; no code changes. Results are
  intentionally not piped through `apply_ingest` — host-native results
  lack DOI/authors/venue and would erode the corpus audit trail.


## 0.15.0 — 2026-05-12

### Features

- New `list_sources.py` script + `SOURCE_META` constant on every
  `search_*.py`. Orchestrators can now query the federated search
  registry by domain, index type, auth requirement, or
  needs-relevance-filter flag — no more grepping each script's
  docstring to plan which sources to hit. Schema in `_search_meta.py`,
  validated at discovery, errors surfaced under `validation_warnings`.


## 0.14.3 — 2026-05-12

### Internal refactor

- Adopt [towncrier](https://towncrier.readthedocs.io) for incremental
  changelog management. New PRs drop a fragment in `changelog.d/<slug>.<type>.md`
  and `towncrier build --version X.Y.Z` aggregates them at release time —
  no more hand-editing `CHANGELOG.md`. Past releases (0.13.x → 0.14.2)
  reconstructed from git log for completeness.

## 0.14.2 — 2026-05-12

### Features

- `safe_get()` SSRF guard in `_common.py`: resolves the URL host and
  refuses to fetch when the IP is private/loopback/link-local/reserved.
  Wired into the two user/upstream-controlled URL sites — `extract_pdf.py
  --url` and the Unpaywall-resolved `pdf_url` in `_pdf_fetch.py`. New
  `ssrf_refused` error code maps to `EXIT_VALIDATION` and the envelope
  carries a `next:` hint pointing to `--input` as the fallback.

### Internal refactor

- Replaced 4 silent `except ... pass` sites with `logger.debug()` calls
  (search-cache parse/write, advisory state writes, msvcrt unlock).
  Stdout stays envelope-only; diagnostics route through stderr.

## 0.14.1 — 2026-05-12

### Features

- `extract_pdf.py` gains `--ocr-backend
  {auto,rapidocr,ocrmac,easyocr,tesseract,none}` and `--ocr-lang
  <comma-list>`. `none` skips OCR entirely (saves ~10s model load on
  known-clean PDFs); the others force a specific docling backend. Meta
  now reports `ocr_backend` / `ocr_lang` / `do_ocr` for auditability.

## 0.14.0 — 2026-05-12

### Features

- New `--engine {auto,pypdf,docling}` flag on `extract_pdf.py`.
  `auto` (default) runs pypdf first and upgrades to docling (markdown
  output, layout-aware, built-in OCR) when the pypdf result looks
  scanned/sparse. docling is an optional dep (`pip install docling`);
  `auto` degrades gracefully with `engine_fallback_reason` when absent.
- `extract_pdf.py` gains `--idempotency-key`: cache stores the extracted
  text alongside meta so retries rewrite the `--output` file rather than
  just replaying the envelope.

### Documentation

- Phase 3 deep-read prompt now uses `.md` suffix for extracted text and
  explains the engine selector.

## 0.13.3 — earlier

- Drop metadata garbage at citation-chase ingest (P2.10).

## 0.13.2 — earlier

- Pin v0.13.0 features with 57 new unit tests.

## 0.13.1 — earlier

- Per-source rate limiter for arXiv / PubMed / DBLP.

## 0.13.0 — earlier

- Fix gate / relevance / escape-hatch issues found by end-to-end test
  run.
