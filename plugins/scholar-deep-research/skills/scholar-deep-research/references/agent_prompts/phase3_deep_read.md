# Phase 3 — Parallel Deep-Read Agent Prompt Template

This file is loaded on demand by the host LLM during Phase 3, after `skim_papers.py` has assigned tiers. The host dispatches **one agent per `tier=deep` paper**, in parallel waves of 8–10 (see "Wave sizing" below). Each agent runs the prompt below in isolation and writes evidence back to `research_state.json` via the shared CLI — the host's main context only sees the one-line return.

## Why parallel agents (and not a single async script)

Phase 3 is reasoning-heavy, not I/O-heavy: the agent has to read the paper, decide what counts as a finding vs. background, link claims to evidence, and judge limitations. Compressing that into a deterministic Python loop loses the reasoning. Compressing 50 papers' worth of full-text into the host's main context wastes tokens. Parallel agents put each paper's reasoning in its own ~200-token context bubble; only the structured evidence record returns.

## Wave sizing

- **Default:** waves of 8–10 agents per dispatch message.
- **Why batch:** more than ~10 simultaneous tool_use blocks risk host-side rate limits and back-pressure. Smaller waves also let you abort cheaply if the first 1–2 results look wrong.
- **Total cost** is roughly linear in deep-tier count, so trim aggressively at triage time (`skim_papers.py --deep-ratio 0.3`) when budget is tight.

## Per-agent prompt (copy-paste; fill in the `${...}` placeholders)

```
You are a Phase 3 deep-read agent for the scholar-deep-research skill.

## Your single paper

paper_id   : ${paper_id}        # e.g. "doi:10.1038/s41586-020-2649-2"
title      : ${title}
doi        : ${doi}             # may be null — fall back to pdf_url
pdf_url    : ${pdf_url}         # may be null
pdf_path   : ${pdf_path}        # may be null. If set AND file exists, use it
                                # directly — prefetch_pdfs.py already pulled
                                # the PDF, no network call needed.
abstract   : ${abstract}        # already in state; use as a fallback if PDF fetch fails

## Research question (Phase 0)

${question}

## What you must do

1. Get the full text. Try in this order, stopping at the first that yields >2000 chars:
   a. **If `pdf_path` is provided AND points at an existing file** (`prefetch_pdfs.py` ran):
      ```
      python scripts/extract_pdf.py --input '${pdf_path}' --output /tmp/${safe_id}.txt
      ```
      No network call — fastest path. **Always prefer this when available.**
   b. `python scripts/extract_pdf.py --doi '${doi}' --output /tmp/${safe_id}.txt`
      (uses the paper-fetch skill's 5-source OA chain when installed)
   c. `python scripts/extract_pdf.py --url '${pdf_url}' --output /tmp/${safe_id}.txt`
   d. If all fail: write evidence_unavailable (see "Failure mode" below) and stop.

   If `pdf_path` is set but the file is missing (cache wiped between prefetch
   and dispatch), fall through to (b). Do **not** silently skip — that path
   is what `pdf_status='failed'` already records, and re-attempting via (b)
   gives the paper one more chance with a different transport.

2. Read the extracted text. Extract per-paper evidence covering:
   - method            : 1 sentence on the experimental/computational approach
   - findings          : 3–5 bullets, each with a section/page anchor where possible
                         (e.g. "ABE7.10 corrects 65% of dystrophin in mdx mice (Fig 3a)")
   - limitations       : what the paper itself acknowledges + what you noticed
   - relevance         : 1–2 sentences on how this moves the question forward

3. Write evidence back to state. **Prefer the JSON path** — it skips
   the multi-quote shell escape dance that bites when findings contain
   single quotes, unicode, or section headers:

   ```bash
   echo '${json_payload}' | python scripts/research_state.py \
     --state ${state_path} evidence --id '${paper_id}' --from-json -
   ```

   Where `${json_payload}` is `{"method": "...", "findings": ["...", ...],
   "limitations": "...", "relevance": "...", "depth": "full"}`. JSON's
   `depth` wins over the `--depth` flag.

   Structured mode is still supported for short single invocations:
   ```bash
   python scripts/research_state.py --state ${state_path} evidence \
     --id '${paper_id}' --depth full \
     --method '${method}' \
     --findings '${finding_1}' '${finding_2}' '${finding_3}' \
     --limitations '${limitations}' \
     --relevance '${relevance}'
   ```

   The CLI is exclusive-locked — N agents writing concurrently are serialized
   automatically; no coordination needed.

4. Return EXACTLY one JSON line to the host (no prose):
   ```json
   {"paper_id": "${paper_id}", "status": "ok", "evidence_chars": <int>, "method_brevity": <int>}
   ```

## Failure modes

There are two escape hatches that count as valid deep-tier coverage so a
single bad paper does not block the whole workflow. Both keep `depth='shallow'`
and prefix `evidence.method` with a magic string the gate recognises.

### Failure mode A — full text unreachable

Paywall, exhausted OA chain, scanned PDF, dead link. The PDF was *not* read.

```bash
python scripts/research_state.py --state ${state_path} evidence \
  --id '${paper_id}' --depth shallow \
  --method 'evidence_unavailable: ${reason_code}' \
  --findings 'No full text available; abstract excerpt: ${abstract_excerpt}' \
  --limitations 'Marked evidence_unavailable; do not cite as sole source.' \
  --relevance 'Pending source recovery.'
```

Reason codes: `paywall_no_oa`, `pdf_fetch_failed`, `scanned_no_ocr`, `dead_link`.

Return:
```json
{"paper_id": "${paper_id}", "status": "evidence_unavailable", "reason": "${reason_code}"}
```

### Failure mode B — PDF read but topic mismatch

The PDF *was* extracted in full and you read it, but the paper turned out to
be off-topic — Phase 2 ranking surfaced it on surface-token overlap (e.g. it
shares words like "evaluation" or "LLM" with the question but is actually
about a different problem). Record what little is usable and tag the
mismatch so the synthesis can treat the paper as a contrast/baseline rather
than a primary source. Do not silently mark it as `depth='full'` — the
relevance flag matters for the report.

```bash
python scripts/research_state.py --state ${state_path} evidence \
  --id '${paper_id}' --depth shallow \
  --method 'topic_mismatch: ${one_sentence_what_paper_is_actually_about}' \
  --findings '${useful_observation_1}' '${useful_observation_2}' \
  --limitations 'Off-topic vs Phase 0 question; cite as contrast/baseline only, not primary evidence.' \
  --relevance '${one_sentence_what_the_paper_can_anchor_in_the_report}'
```

Return:
```json
{"paper_id": "${paper_id}", "status": "topic_mismatch", "evidence_chars": <int>}
```

## Constraints

- DO NOT call MCP tools. Phase 3 must run offline-first.
- DO NOT modify any state field other than `papers[<id>].evidence` and `papers[<id>].depth`. The CLI enforces this; do not try to work around it.
- DO NOT chain into Phase 4 (citation chase) or Phase 5 (synthesis). One paper, one evidence record, one return.
- Findings MUST be specific (numbers, conditions, comparisons), not generic ("the authors found that base editing works"). Generic findings are worse than no finding — they silently inflate G4's coverage count without contributing to the report.
```

## Host-side dispatch (single message, multiple Agent tool_use blocks)

After `skim_papers.py` reports `counts.deep`, the host LLM:

1. Loads this template once.
2. For each `paper_id` with `tier == "deep"`, instantiates the prompt with the per-paper substitutions.
3. Sends a **single message containing all N tool_use blocks** so they fan out in parallel. (In Claude Code: one assistant message with N `Agent` tool calls; subagent_type `general-purpose`.)
4. After the wave returns, runs:

```bash
python scripts/research_state.py --state ${state_path} advance --to 4 --check-only
```

If `deep_tier_full_evidence` is still failing, dispatch a second wave for the missing ids only.

## Recovery after a partial wave

If 7/10 agents returned `status:"ok"` and 3 returned `status:"evidence_unavailable"` (or timed out), do **not** retry the failed three immediately. First inspect `state.papers[<id>].evidence`:

- `evidence.method` starts with `evidence_unavailable:` → genuine OA chain failure. Either accept the shallow record or open the URL manually and feed it through `extract_pdf.py --input <local.pdf>`.
- No `evidence` field at all → agent crashed before write. Re-dispatch one agent for that id.

The state CLI is idempotent on `evidence` (re-writing the same id overwrites the record), so re-dispatching is safe.
