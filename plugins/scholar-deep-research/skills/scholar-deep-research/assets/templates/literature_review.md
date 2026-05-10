# {{title}}: A Literature Review

**Question:** {{question}}
**Date:** {{date}}
**Sources consulted:** {{sources}}
**Papers in corpus:** {{total_papers}} ({{selected_count}} selected for deep read)

---

## Executive summary

- {{bullet 1}}
- {{bullet 2}}
- {{bullet 3}}
- {{bullet 4 — optional}}
- {{bullet 5 — optional}}

## 1. Background

Define key terms, scope, and why this matters. Two-three short paragraphs.
Every non-trivial claim is anchored: `claim [^id1][^id2]`.

## 2. {{theme 1 name}}

Synthesize what the corpus says about this theme.

- Sub-finding A [^id]
- Sub-finding B [^id1][^id2]

If a tension lives in this theme, surface it here:

> **Tension:** {{topic}}. {{position A}} [^id1][^id2] vs {{position B}} [^id3].
> Empirical / methodological / theoretical disagreement.

## 3. {{theme 2 name}}

Same shape.

## 4. {{theme 3 name}}

Same shape. Add more themes (max ~6) as needed.

## 5. Synthesis

What does the corpus collectively say? This is the section that earns the report.
Don't just summarize — argue. Where do the themes connect? What is the dominant view? Where is the field actually moving?

## 6. Open questions and gaps

- Gap 1: {{description}} — no studies in corpus address {{specific subquestion}}
- Gap 2: {{description}} — only one paper [^id] tackles this and has not been replicated
- Gap 3: {{description}} — recency: nothing newer than {{year}}

## 7. Recommendations for further reading

If the user wants to go deeper, start here:

1. {{paper 1}} [^id] — {{why}}
2. {{paper 2}} [^id] — {{why}}
3. {{paper 3}} [^id] — {{why}}

## Appendix A — Methodology

**Search strategy:**
- Sources: {{sources}}
- Clusters: {{clusters}}
- Rounds: {{round count}} per cluster
- Saturation: hit at round {{n}} (new={{pct}}%, max_new_citations={{n}})

**Ranking formula:**
```
{{state.ranking.formula}}
```
Weights: α={{alpha}}, β={{beta}}, γ={{gamma}}, δ={{delta}}, half-life={{half_life}}y

**Selection:** top {{N}} by score. Selected papers and component scores in `state.papers[*].score_components`.

## Appendix B — Self-critique

{{self_critique.appendix}}

## Bibliography

{{rendered from export_bibtex.py --format bibtex}}
