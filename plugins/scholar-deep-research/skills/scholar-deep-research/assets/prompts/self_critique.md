# Self-critique checklist (Phase 6)

Read your draft with adversarial intent. Write findings to `state.self_critique.findings` via:

```bash
python scripts/research_state.py critique --finding "..."
```

When all findings are addressed (resolved) or explicitly accepted, write the appendix:

```bash
python scripts/research_state.py critique --appendix "$(cat critique_summary.md)"
```

The appendix is copied verbatim into the report. Don't sanitize it — readers deserve to see what the process doubted itself about.

---

## The checklist

Work top to bottom. For each item, write a one-line finding even if the answer is "checked, no issue found, here's why."

### 1. Unanchored claims
Scan the draft for sentences that make a non-trivial assertion without `[^id]`. Each one is either:
- a hallucination (remove or anchor)
- a definitional sentence that's OK without an anchor (mark as such)

### 2. Single-source claims
For every claim with exactly one anchor, ask: would the report still be honest if that one paper turned out to be wrong? If not, find a corroborating anchor or downgrade the claim.

### 3. Citation skew — venue
Run `python scripts/research_state.py query selected` and tally venues. If one venue accounts for >60% of selected papers, note it. Either justify (the field really is that concentrated) or broaden.

### 4. Citation skew — author
Same for first authors and senior (last) authors. >40% from one lab is a flag.

### 5. Recency coverage
What's the most recent year in the selected set? If the latest 18 months are absent, run a final search round restricted to that window. Re-rank. Re-select.

### 6. Untested high-citation papers
Identify the top 3 papers by citation count in the selected set. For each, check whether the corpus contains any critique, replication, or failed reproduction. If not, search explicitly:
```
"<first author> <year>" (critique OR limitation OR replication OR challenge)
```
Even a "no critique exists" finding is a legitimate result — note it.

### 7. Buried tensions
Re-read `state.tensions`. For each tension, find where it appears in the draft. If a tension was documented in Phase 5 but doesn't appear in the body, you buried it. Surface it.

### 8. Archetype fit
Look at the chosen archetype's structure (in `references/report_templates.md`). Does the draft actually follow it? A draft that secretly drifted from `comparative_analysis` to `literature_review` is a sign you should re-pick.

### 9. Preprint flagging
Every paper with `source: arxiv` and no journal DOI should render as `[^id, preprint]` in the body. Grep for these IDs and check.

### 10. Methodology appendix
Is the methodology appendix populated? It should include: queries run, sources, dedupe stats, ranking formula, weights, and selection size. If it's a stub, fill it from `state.queries` and `state.ranking`.

### 11. Saturation actually happened
Did Phase 1 actually saturate, or did it stop because the model got tired? Check:
```bash
python scripts/research_state.py saturation
```
If the last round wasn't saturated, run more rounds before publishing.

### 12. Counter-arguments
Is there a strong counter-argument the report doesn't engage with? If your topic is contested at all, the absence of opposition in the draft is itself suspicious.

### 13. The "honest reader" test
If the user reads this report and then reads one of the papers it cites, will they feel misled? Find any place where the summary in the draft is significantly more confident than the source paper's own framing.

### 14. The "ten years from now" test
If a critic reads this report in ten years and the field has moved on, what would embarrass us most? That answer is the gap to mention in the limitations.

---

## Appendix template

Once you're done, the appendix you write to state should look something like this:

```markdown
## Self-critique findings

The Phase 6 self-critique checked the following items. Findings noted, with resolutions:

1. **Unanchored claims** — found 3 sentences without anchors. All resolved (1 removed, 2 anchored to existing papers).
2. **Single-source claims** — 4 claims rested on single papers. 2 corroborated with additional searches; 2 explicitly downgraded ("only one study to date reports this").
3. **Venue skew** — selected papers were 38% Nature/Cell/Science; not flagged as a problem given the field.
4. **Recency** — latest paper in original selection was {{year-1}}. Ran a final search restricted to the last 18 months and added 4 papers.
5. **Untested high-citation papers** — top-cited paper [^id] had no critique in corpus. Targeted search returned a {{year}} commentary [^id2] questioning the {{aspect}}; added to corpus and incorporated into Section X.
6. **Buried tensions** — {{0 / 1 / N}} tensions surfaced in the body; {{0 / 1 / N}} were already there.
7. **Other findings** — {{...}}

Items where no issue was found are listed in the README of state.self_critique for completeness.
```

The appendix is short, honest, and dated. Future readers know what the report's blind spots were, and that itself is part of the contribution.
