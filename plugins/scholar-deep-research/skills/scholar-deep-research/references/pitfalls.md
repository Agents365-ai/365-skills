# Pitfalls

Long-form catalog of failure modes. The SKILL.md has the short list; this file is for when something feels off and you want to debug *what kind* of off it is.

## 1. First-page fixation

**Symptom:** the report draws heavily from the first 10 OpenAlex hits, ignores everything past page 1.

**Why it happens:** search engines are good at returning relevant-looking results; the model anchors on whatever appears first.

**Fix:** require ≥3 search rounds per cluster, and explicitly check that the top-N selected papers do not all come from the first round of any single cluster.

**Detection:** in state, look at `papers[*].first_seen_round`. If 80%+ of selected papers have `first_seen_round=1`, you fixated.

## 2. Unanchored claims

**Symptom:** the draft contains assertions like "it is widely believed that..." or "studies have shown..." without `[^id]` anchors.

**Why it happens:** the model has prior knowledge that isn't sourced from the corpus; it leaks in.

**Fix:** treat any non-trivial claim without an anchor as a hallucination. Either find a paper in state to anchor it, or remove the claim. The Phase 6 self-critique pass catches these.

## 3. Confirmation bias

**Symptom:** every cited paper supports the same position; no tensions documented in Phase 5.

**Why it happens:** keyword choice and citation chasing both reinforce existing framings. If your seed papers all share an assumption, snowballing won't break out.

**Fix:** in Phase 4, explicitly search for `"<top author> critique"`, `"<key term> failed replication"`, `"<consensus claim> challenged"`. Add a Round of negative-keyword search.

**Detection:** if `state.tensions` is empty AND your topic is non-trivial, you almost certainly have confirmation bias.

## 4. Preprint conflation

**Symptom:** the report cites an arXiv paper as if it were peer-reviewed.

**Why it happens:** preprints look like papers. The schema does mark `source: arxiv`, but the model can forget.

**Fix:** every citation in the bibliography that has only `source: ["arxiv"]` and no DOI should render as `[^id, preprint]` in the body. Make this a self-critique check.

## 5. Venue monoculture

**Symptom:** >60% of selected papers come from one journal or one conference series.

**Why it happens:** OpenAlex's relevance scoring + citation prior favors high-prestige venues, which creates a feedback loop.

**Fix:** in Phase 6, run `python scripts/research_state.py query selected | jq '.[] | .venue' | sort | uniq -c | sort -rn` (or equivalent). If one venue is >60%, broaden the search clusters or add a different source.

## 6. Author monoculture

**Symptom:** one lab or one author appears as first/last author in 5+ selected papers.

**Why it happens:** snowballing inside an active lab's network. The lab's papers cite each other, and the citation chase amplifies that.

**Fix:** re-run search with `NOT author:<dominant author>` in one round, just to surface the alternatives. Then re-rank.

## 7. Recency collapse

**Symptom:** saturation hit before the most recent year was well-covered. Top-N has no 2025 papers.

**Why it happens:** older papers have more citations, so they win the rank. The recency component (γ) is intentionally light, so it can be overwhelmed.

**Fix:** always run a final search round restricted to the last 18 months: `--year-from 2024`. Re-dedupe and re-rank.

## 8. Stale MCP tool names

**Symptom:** the workflow references `mcp__asta__search_papers_by_relevance` but the tool is unavailable, or has been renamed.

**Why it happens:** MCP servers rename tools without warning. The skill's scripts are stable; MCP names are not.

**Fix:** before using any MCP tool, list the actually-available tools. The pipeline does not depend on MCP — scripts cover all critical paths.

## 9. Single-shot search

**Symptom:** one search round, then off to the report.

**Why it happens:** the model is in a hurry. Saturation didn't fire because the threshold was never tested.

**Fix:** the completion gate for Phase 1→2 requires `state.queries` to have ≥3 entries from primary sources. Enforce.

## 10. Skipping self-critique

**Symptom:** Phase 6 was logged as "looks good, no findings."

**Why it happens:** the temptation to ship a clean draft is highest at the moment Phase 6 catches the most.

**Fix:** Phase 6 must produce findings — either real ones or an explicit "I checked X, Y, Z and found no issues, with reasoning." An empty `state.self_critique.findings` is itself a flag.

## 11. Lossy abstract reading

**Symptom:** evidence section fields are filled, but they don't actually match the paper's findings.

**Why it happens:** the model read the title + abstract, projected what it thought the paper said, and wrote that into evidence.

**Fix:** for every paper in the top-N, deep-read the full text (not just abstract) when available, and require evidence fields to cite section numbers or page numbers.

## 12. Stale facts from training data

**Symptom:** the report includes a "well-known fact" that turns out to be from the model's training data, not the corpus.

**Why it happens:** the model is genuinely helpful and adds context. The context isn't from your sources.

**Fix:** the anchor rule (every claim has `[^id]`) catches this. If you can't anchor it, you can't claim it.

## 13. Brittle DOIs

**Symptom:** the bibliography has DOIs that 404, or the same paper appears twice with slightly different DOIs.

**Why it happens:** Crossref has multiple DOIs for some works (preprint DOI + journal DOI). OpenAlex sometimes records a placeholder.

**Fix:** the dedupe script normalizes by lowercase DOI. Run it after every ingest. For papers with multiple DOIs, prefer the journal DOI (the one returned by Crossref).

## 14. Black-box ranking

**Symptom:** the user asks why paper X is in the top-N and you can't say.

**Why it happens:** the ranking formula is buried in script defaults.

**Fix:** every report has a methodology appendix that prints `state.ranking.formula` and `state.ranking.weights`. Per-paper components live in `state.papers[id].score_components`. Show your work.
