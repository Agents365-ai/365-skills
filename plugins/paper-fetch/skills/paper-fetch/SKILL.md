---
name: paper-fetch
description: Use whenever the user wants to obtain, download, or fetch a paper's PDF — given a DOI, an arXiv id, a paper title, a citation, or a list of DOIs. Trigger on phrases like "download this paper", "find the PDF for [DOI]", "grab me the [Nature/bioRxiv/arXiv] paper on X", "get the open-access version", "I need this article", or any bulk/batch paper download request, even when the user doesn't explicitly say "PDF" or "DOI". Resolves via Unpaywall → Semantic Scholar → arXiv → PubMed Central → bioRxiv/medRxiv → publisher direct (institutional opt-in) → Sci-Hub mirrors as last-resort fallback.
homepage: https://github.com/Agents365-ai/paper-fetch
metadata: {"openclaw":{"requires":{"bins":["python3"]},"emoji":"📄"},"pimo":{"category":"research","tags":["paper","pdf","doi","open-access","download"]},"author":"Agents365-ai","version":"0.13.1"}
---

# paper-fetch

Fetch the PDF for a paper given a DOI (or title). Tries multiple sources in priority order and stops at the first hit.

## Resolution order

1. **Unpaywall** — `https://api.unpaywall.org/v2/{doi}?email=$UNPAYWALL_EMAIL`, read `best_oa_location.url_for_pdf` (skipped if `UNPAYWALL_EMAIL` not set)
2. **Semantic Scholar** — `https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields=openAccessPdf,externalIds`
3. **arXiv** — if `externalIds.ArXiv` present, `https://arxiv.org/pdf/{arxiv_id}.pdf`
4. **PubMed Central OA** — if PMCID present, `https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/`
5. **bioRxiv / medRxiv** — if DOI prefix is `10.1101`, query `https://api.biorxiv.org/details/{server}/{doi}` for the latest version PDF URL
6. **Publisher direct** *(institutional mode only — `PAPER_FETCH_INSTITUTIONAL=1`)* — DOI-prefix → publisher PDF template (Nature / Science / Wiley / Springer / ACS / PNAS / NEJM / Sage / T&F / Elsevier). The caller's own subscription IP / cookies / EZproxy are what authorize the fetch; unauthorized responses fail the `%PDF` check and fall through to step 7.
7. **Sci-Hub mirrors** *(on by default; disable with `PAPER_FETCH_NO_SCIHUB=1`)* — last-resort fallback. Tries the mirror list in `PAPER_FETCH_SCIHUB_MIRRORS` (or built-in defaults `sci-hub.ru`, `sci-hub.st`, `sci-hub.su`, `sci-hub.box`, `sci-hub.red`, `sci-hub.al`, `sci-hub.mk`, `sci-hub.ee`) in order; on full miss, scrapes `https://www.sci-hub.pub/` once per process for fresh mirrors. CAPTCHA / missing-paper pages have no PDF iframe and fall through silently.
8. Otherwise → report failure with title/authors so the user can request via ILL

If only a title is given, pass it directly via `--title "<title>"`. Resolution chain:

1. **Crossref** `query.title` — primary; covers all major journal/conference DOIs
2. **Semantic Scholar `/paper/search/match`** — fallback when Crossref's top match is low-confidence (`match_score < 40`) or the gap to the runner-up is `< 3`. Critically, S2 covers arXiv-only preprints (no Crossref DOI). When S2 surfaces a paper that has only an arXiv id, the canonical `10.48550/arXiv.<id>` is synthesized so the download chain stays uniform.
3. **Crossref's best guess (low-confidence)** — used only when both resolvers struggled. The result envelope sets `meta.title_resolution.low_confidence: true` plus a `low_confidence_reason` (`score_below_threshold` / `ambiguous_runner_up`) so an agent can either bail or confirm via `--dry-run`.

Either way the resolved DOI, the winning resolver, the full `resolvers_tried` list, and the top candidate matches are all surfaced under `meta.title_resolution`.

**If `semanticscholar-skill` is registered**, it can serve as a richer pre-step for title → DOI resolution — useful when you also need relevance ranking, snippet search, or citation context, not just a DOI. The agent writes a Python script using the skill's `match_title()` to read `externalIds.DOI`, then runs `paper-fetch <doi>`. When the result has only an `ArXiv` id (no DOI), synthesize `10.48550/arXiv.<ArXiv>` and pass that to paper-fetch.

When only the DOI is needed, `--title` is the single-command path — paper-fetch's built-in Crossref → S2 chain handles most cases.

## Usage

```bash
python scripts/fetch.py <DOI> [options]
python scripts/fetch.py --title "<paper title>" [options]
python scripts/fetch.py --batch <FILE|-> [options]
python scripts/fetch.py schema           # machine-readable self-description
```

### Flags

The flags below are the ones an agent composes in normal use. For the complete contract — including `--dry-run`, `--pretty`, `--stream`, `--overwrite`, `--timeout`, `--version`, plus parameter types and exit-code mappings — run `python scripts/fetch.py schema` (machine-readable, drift-checked via `schema_version`).

| Flag | Default | Description |
|------|---------|-------------|
| `doi` | — | DOI to fetch (positional). Use `-` to read a single DOI from stdin |
| `--title TITLE` | — | Paper title; resolved to a DOI via Crossref before download. Mutually exclusive with positional DOI / `--batch` |
| `--batch FILE` | — | File with one DOI per line for bulk download. Use `-` to read from stdin |
| `--out DIR` | `pdfs` | Output directory |
| `--format` | auto | `json` for agents, `text` for humans. Auto-detects: `json` when stdout is not a TTY, `text` when it is |
| `--idempotency-key KEY` | — | Safe-retry key. Re-running with the same key replays the original envelope from `<out>/.paper-fetch-idem/` without network I/O |

### Agent discovery: `schema` subcommand

```bash
python scripts/fetch.py schema
```

Emits a complete machine-readable description of the CLI on stdout (no network). Includes `cli_version`, `schema_version`, parameter types, exit codes, error codes, envelope shapes, and environment variables. Agents should read this once, cache it against `schema_version`, and re-read when the cached version drifts.

### Output contract

**stdout** emits a single JSON envelope. Every envelope carries a `meta` slot.

**Success** (all DOIs resolved):

```json
{
  "ok": true,
  "data": {
    "results": [
      {
        "doi": "10.1038/s41586-021-03819-2",
        "success": true,
        "source": "unpaywall",
        "pdf_url": "https://www.nature.com/articles/s41586-021-03819-2.pdf",
        "file": "pdfs/Jumper_2021_Highly_accurate_protein_structure_predic.pdf",
        "meta": {"title": "Highly accurate protein structure prediction with AlphaFold", "year": 2021, "author": "Jumper"},
        "sources_tried": ["unpaywall"]
      }
    ],
    "summary": {"total": 1, "succeeded": 1, "failed": 0},
    "next": []
  },
  "meta": {
    "request_id": "req_a908f5156fc1",
    "latency_ms": 2036,
    "schema_version": "1.9.0",
    "cli_version": "0.13.1",
    "sources_tried": ["unpaywall"]
  }
}
```

**Partial** (batch mode — some DOIs failed, exit code reflects the failure class):

```json
{
  "ok": "partial",
  "data": {
    "results": [
      { "doi": "10.1038/s41586-021-03819-2", "success": true, "source": "unpaywall", ... },
      {
        "doi": "10.1234/nonexistent",
        "success": false,
        "source": null,
        "pdf_url": null,
        "file": null,
        "meta": {},
        "sources_tried": ["unpaywall", "semantic_scholar"],
        "error": {
          "code": "not_found",
          "message": "No open-access PDF found",
          "retryable": true,
          "retry_after_hours": 168,
          "reason": "OA availability changes over time; retry after embargo lifts or preprint appears"
        }
      }
    ],
    "summary": {"total": 2, "succeeded": 1, "failed": 1},
    "next": ["paper-fetch 10.1234/nonexistent --out pdfs"]
  },
  "meta": { ... }
}
```

The `next` slot is an array of suggested follow-up commands: re-invoking them retries only the failed subset. Combine with `--idempotency-key` to make the whole batch safely retriable without re-downloading the already-succeeded items.

**Failure** (bad arguments, exit code 3):

```json
{
  "ok": false,
  "error": {
    "code": "validation_error",
    "message": "Provide a DOI or --batch file",
    "retryable": false
  },
  "meta": { ... }
}
```

**Per-item skipped** (destination already exists, no `--overwrite`):

```json
{
  "doi": "10.1038/s41586-021-03819-2",
  "success": true,
  "source": "unpaywall",
  "pdf_url": "https://...",
  "file": "pdfs/Jumper_2021_...pdf",
  "skipped": true,
  "skip_reason": "file_exists",
  "sources_tried": ["unpaywall"]
}
```

**Idempotency replay** (re-run with the same `--idempotency-key`):

The cached envelope is returned verbatim, but `meta.request_id` and `meta.latency_ms` are re-stamped for the current call, and `meta.replayed_from_idempotency_key` is set. No network I/O occurs.

### Stderr progress (NDJSON)

When `--format json`, stderr emits one JSON object per line for liveness:

```
{"event": "session",     "request_id": "req_...", "elapsed_ms": 0,    "cli_version": "0.13.1", "schema_version": "1.9.0"}
{"event": "start",       "request_id": "req_...", "elapsed_ms": 2,    "doi": "10.1038/..."}
{"event": "source_try",  "request_id": "req_...", "elapsed_ms": 2,    "doi": "...", "source": "unpaywall"}
{"event": "source_hit",  "request_id": "req_...", "elapsed_ms": 2036, "doi": "...", "source": "unpaywall", "pdf_url": "..."}
{"event": "download_ok", "request_id": "req_...", "elapsed_ms": 4120, "doi": "...", "file": "..."}
```

Event types: `session`, `start`, `source_try`, `source_hit`, `source_miss`, `source_skip`, `source_enrich`, `source_enrich_failed`, `download_ok`, `download_error`, `download_skip`, `dry_run`, `not_found`. All events share `request_id` and `elapsed_ms`, letting an orchestrator correlate progress across stderr and the final stdout envelope. The `session` event fires once per invocation, before any DOI work or network I/O, and carries `cli_version` / `schema_version` so agents can detect schema drift against a cached copy without waiting for the final envelope.

`source_enrich` fires when Semantic Scholar is called purely to backfill missing `author` / `title` after another source already provided the PDF URL; its `fields` array lists exactly which fields were filled in. `source_enrich_failed` fires when that enrichment call fails — the Unpaywall PDF URL is still used and the filename falls back to `unknown_<year>_…`.

When `--format text`, stderr emits human-readable prose.

### Exit codes

| Code | Meaning | Retryable class |
|------|---------|-----------------|
| `0` | All DOIs resolved / previewed | — |
| `1` | Unresolved — one or more DOIs had no OA copy; no transport failure | Not now (retry after `retry_after_hours`) |
| `2` | Reserved for auth errors (currently unused) | — |
| `3` | Validation error (bad arguments, missing input) | No |
| `4` | Transport error (network / download / IO failure) | Yes |

The taxonomy lets an orchestrator route failures deterministically: exit 4 is worth retrying immediately, exit 1 is not, exit 3 is a bug in the caller.

### Error codes in JSON

Every retryable error carries a `retry_after_hours` hint in the error object, so an orchestrator can schedule retries without guessing.

| Code | Meaning | Retryable | `retry_after_hours` |
|------|---------|-----------|---------------------|
| `validation_error` | Bad arguments or empty input | No | — |
| `title_resolve_failed` | Crossref returned no items for the given `--title` query (try a longer / cleaner title, or pass the DOI directly) | No | — |
| `not_found` | No open-access PDF found | Yes | `168` (one week — OA lands on embargo / preprint timescale) |
| `download_network_error` | Network failure during download | Yes | `1` |
| `download_not_a_pdf` | Response was not a PDF (HTML landing page) | No | — |
| `download_host_not_allowed` | PDF URL failed SSRF safety check (private IP / non-http(s) / non-80,443 / blocked metadata host) | No | — |
| `download_size_exceeded` | Response exceeded 50 MB limit | Yes | `24` |
| `download_io_error` | Local filesystem write failed | Yes | `1` |
| `internal_error` | Unexpected error | No | — |

The canonical mapping lives in `RETRY_AFTER_HOURS` in `scripts/fetch.py` and is surfaced in `schema.error_codes`.

### Examples

```bash
# Single DOI (JSON output when piped; text when in a terminal)
python scripts/fetch.py 10.1038/s41586-020-2649-2

# Single title (resolved to DOI via Crossref, then downloaded)
python scripts/fetch.py --title "Highly accurate protein structure prediction with AlphaFold"

# Dry-run preview (resolve without downloading)
python scripts/fetch.py 10.1038/s41586-020-2649-2 --dry-run

# Title + dry-run — preview the resolved DOI and candidate matches
python scripts/fetch.py --title "Attention Is All You Need" --dry-run

# Force JSON (for agents even inside a terminal)
python scripts/fetch.py 10.1038/s41586-020-2649-2 --format json

# Human-readable with pretty colors in a pipeline
python scripts/fetch.py 10.1038/s41586-020-2649-2 --format text

# Batch download, safely retriable
python scripts/fetch.py --batch dois.txt --out ./papers \
    --idempotency-key monday-review-batch

# Pipe DOIs from another tool
zot -F ids.json query ... | jq -r '.[].doi' | python scripts/fetch.py --batch -

# Agent discovery
python scripts/fetch.py schema --pretty

# Streaming mode — one result per line as each DOI resolves
python scripts/fetch.py --batch dois.txt --stream

# Works without UNPAYWALL_EMAIL (skips Unpaywall, uses remaining 4 sources)
python scripts/fetch.py 10.1038/s41586-020-2649-2
```

## Environment

| Variable | Default | Purpose |
|---|---|---|
| `UNPAYWALL_EMAIL` | unset | Contact email for Unpaywall API. Optional but recommended. Without it, Unpaywall is skipped (remaining sources still work). |
| `PAPER_FETCH_INSTITUTIONAL` | unset | Set to any value (e.g. `1`) to opt into **institutional mode** — activates a 1 req/s rate limiter and the publisher-direct fallback. See below. |
| `PAPER_FETCH_NO_SCIHUB` | unset | Set to any value to disable the Sci-Hub fallback (step 7). |
| `PAPER_FETCH_SCIHUB_MIRRORS` | unset | Comma-separated mirror hostnames to try in priority order (e.g. `sci-hub.ru,sci-hub.st,sci-hub.su`). Overrides built-in defaults. |

## Institutional access (opt-in)

Many researchers have legitimate subscription access through their institution's IP range (on-campus or VPN). Paper-fetch can use that access by letting the publisher's own auth (your IP, your session cookies) decide whether to serve the PDF.

Host reachability does not differ between modes — public mode already trusts URLs returned by the OA APIs (Unpaywall, Semantic Scholar, bioRxiv, PMC) and fetches any HTTPS host that passes SSRF defense. Institutional mode adds two things: (1) a **publisher-direct fallback** (step 6 above) that constructs a publisher-side PDF URL by DOI prefix when every OA source missed, so your institutional IP/cookies can authorize the fetch, and (2) a **1 req/s rate limiter** to keep batch jobs from getting your IP throttled or banned for "systematic downloading."

**Opt in:** `export PAPER_FETCH_INSTITUTIONAL=1`

**What changes in institutional mode:**

| Aspect | Public (default) | Institutional |
|---|---|---|
| Host reachability | Any public HTTPS host passing SSRF defense | Same |
| SSRF defense | Enforced (private IP / non-http(s) / non-80,443 / cloud metadata all blocked) | Enforced — same rules |
| Publisher-direct fallback | Off | On — DOI-prefix → publisher PDF URL, last resort after all OA sources miss |
| Rate limit | None | 1 req/s token bucket (all outbound) |
| `meta.auth_mode` | `"public"` | `"institutional"` |

**What stays the same:**

- `%PDF` magic-byte check and 50 MB size cap (prevents HTML landing pages and oversized responses slipping through)
- No CAPTCHA solving, ever. If a publisher shows a challenge, the response won't start with `%PDF` and paper-fetch falls through to the next source.
- No browser automation, no Playwright, no stealth.
- Agent cannot opt in on its own — `PAPER_FETCH_INSTITUTIONAL` must be set by the human operator in the shell environment. This is the trust boundary.

**When paper-fetch can't find an OA copy and you're in public mode**, the error envelope includes `suggest_institutional: true` and a hint telling the user to set the env var. Agents can surface this verbatim rather than failing silently.

**ToS notice:** almost every publisher subscription prohibits "systematic downloading." The 1 req/s rate limit plus the existing per-file idempotency are designed to keep individual research use within acceptable bounds. Running many parallel paper-fetch processes, or lifting the rate limit, can trigger a publisher-wide IP ban affecting your entire institution. Don't.

## Notes

- **Auth is delegated.** The agent never runs a login subcommand. The human or the orchestrator sets `UNPAYWALL_EMAIL` in the environment; the agent inherits it. Missing email degrades gracefully to the remaining 4 sources.
- **Trust is directional.** CLI arguments are validated once at the entry point. SSRF defense, the `%PDF` magic-byte check, and the 50 MB size cap are enforced in the environment layer, not at the agent's request. An agent cannot loosen safety by passing a flag — opting into institutional mode (and its rate-limit risk profile) is an operator action via environment variable.
- **Downloads are naturally idempotent.** Re-running against the same `--out` skips files that already exist (deterministic filename: `{first_author}_{year}_{journal_abbrev}_{short_title}.pdf`; the journal segment is omitted if metadata lacks a journal/venue). Pair with `--idempotency-key` to also replay the exact envelope without any network I/O.
- **Default output directory:** `./pdfs/`.

