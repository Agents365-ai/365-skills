# Changelog

Notable changes to `scholar-deep-research`. Format follows
[Keep a Changelog](https://keepachangelog.com); fragments are managed by
[towncrier](https://towncrier.readthedocs.io) — see `changelog.d/README.md`.

<!-- towncrier release notes start -->

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
