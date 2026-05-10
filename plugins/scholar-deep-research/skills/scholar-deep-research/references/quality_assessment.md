# Quality Assessment

Reference for Phase 3 (Deep read) and Phase 6 (Self-critique). Load this when judging whether a paper deserves the weight it would carry in the report.

## CRAAP test (with adjustments)

The CRAAP framework is from library science but maps cleanly to academic work.

| Letter | Question | What good looks like |
|--------|----------|----------------------|
| **C**urrency | When was this published? | Within field's relevance horizon (2-5 yr in fast fields, decades in others) |
| **R**elevance | Does it match your question? | Title + abstract directly speak to the PICO |
| **A**uthority | Who wrote it, where? | Established lab, peer-reviewed venue, conflict-of-interest disclosed |
| **A**ccuracy | Is the methodology sound? | Pre-registered if possible, sample size justified, code/data available |
| **P**urpose | Why was it written? | Primary research, not advocacy or marketing |

CRAAP is necessary but not sufficient. A CRAAP-perfect paper can still be wrong.

## Venue tiers (rough)

The `rank_papers.py` script uses a small built-in tier-1 list (Nature/Science/Cell/PNAS/NeurIPS/ICML/ICLR/...). Treat it as a starting prior, not a verdict.

**Tier-1 signals (in approximate order of evidential weight):**

1. Replication by an independent group
2. Multiple cited-by criticisms that *failed* to overturn the paper
3. Inclusion in a Cochrane / NICE / FDA / consensus document
4. Published in a top-tier venue
5. High citation count (with attention to *who* is citing)

Citation count alone is a weak signal. A wrong paper can be highly cited (often cited as a counter-example).

## Preprint handling

arXiv, bioRxiv, medRxiv, ChemRxiv, SSRN — none are peer-reviewed.

**Rules:**
- Tag every preprint as `preprint` in the evidence section.
- A claim in the report should not rest *only* on preprints unless the entire report is about pre-registered or in-flight work.
- Check whether the preprint has since appeared in a journal — Crossref by author + title or OpenAlex by title is the fastest check.
- Preprints with >100 citations and >12 months in the wild without journal publication deserve a note: "in pre-print since X, not yet peer reviewed."

## Retraction check

Before deeply citing a paper:

- Look up the DOI on **Retraction Watch** (https://retractionwatch.com) — it's slow but authoritative
- Check OpenAlex `is_retracted: true` flag if available
- Crossref returns a `relation: is-corrected-by` link when an erratum exists

The cost of citing a retracted paper as if it were valid is high. Spend the 30 seconds.

## Conflicts and funding

Note in the evidence section when:
- Funding came from an entity with a direct stake in the result (e.g., drug trial funded by manufacturer)
- Senior author is on the advisory board of a directly-relevant company
- The paper is part of a regulatory dossier, not an independent science paper

This isn't dismissal — it's calibration. A pharma-sponsored Phase 3 trial is still evidence; it's evidence that needs context.

## Sample-size sanity

Quick smell tests by field:

| Field | Suspicious n | Notes |
|-------|--------------|-------|
| Mouse studies | n < 5 per arm | Effect sizes inflate at small n |
| Human RCT | n < 20 per arm | Underpowered for most clinically meaningful effects |
| fMRI / neuroimaging | n < 30 | Voodoo correlations territory |
| Genome-wide association | n < 1000 | Won't survive multiple-testing correction |
| Survey research | n < 200 | Confidence intervals will be huge |
| ML benchmarks | single seed reported | Variance unknown — high risk of cherry-picking |

These are smells, not failures. A well-controlled n=8 mouse experiment can be informative; a sloppy n=80 one isn't.

## When the paper disagrees with the consensus

Two questions to ask:

1. **Did the author engage with the prior consensus?** If they ignore it, they're either revolutionary or ignorant. Both are possible; the methodology section will tell you which.
2. **Did they explain the discrepancy?** If they say "X claimed Y; we find Z because of W methodological choice," that's evidence. If they don't mention X at all, they may not know.

A reasonable report can include a heterodox paper, but the surrounding text should acknowledge that it's heterodox.

## Quick decision tree for Phase 3

```
Have full text? ──no──> mark depth=shallow, fall back to abstract
       │
       yes
       │
Sample size sane? ──no──> mark "low_power" in evidence.limitations
       │
       yes
       │
Pre-registered or replicated? ──yes──> evidence weight = high
       │
       no
       │
Single lab, novel finding, hot field? ──yes──> evidence weight = medium
       │                                       (note as "needs replication")
       no
       │
Established methodology, multiple corroborating papers in corpus?
   ──yes──> evidence weight = high
   ──no──>  evidence weight = medium
```
