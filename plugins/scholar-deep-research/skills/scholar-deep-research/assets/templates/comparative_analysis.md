# {{X}} vs {{Y}}: A Comparative Analysis

**Question:** {{question}}
**Date:** {{date}}
**Sources consulted:** {{sources}}

---

## Executive summary

**Verdict:** {{one-sentence verdict}}

**Confidence:** high / medium / low — {{why}}

**When the verdict flips:** {{edge cases}}

---

## 1. What is being compared

### 1.1 {{X}}
Brief definition, intended use, scope. Who proposes/uses it.

### 1.2 {{Y}}
Same shape.

### 1.3 What is *not* being compared
Explicit exclusions to keep the scope honest.

## 2. Axes of comparison

Each axis: criterion, evidence from corpus, per-axis verdict.

### Axis 1: {{e.g., performance / accuracy}}

| Property | {{X}} | {{Y}} |
|----------|-------|-------|
| Headline metric | {{value}} [^id] | {{value}} [^id] |
| Best-case | ... | ... |
| Worst-case | ... | ... |
| Variance across studies | low/med/high [^id1][^id2] | ... |

**Per-axis verdict:** {{X or Y}} wins on this axis when {{condition}}, but {{caveat}}.

### Axis 2: {{e.g., compute cost / sample efficiency}}
Same shape.

### Axis 3: {{e.g., robustness / generalization}}
Same shape.

### Axis 4: {{e.g., interpretability}}
Same shape.

### Axis 5: {{e.g., maturity / community adoption}}
Same shape.

(Add or remove axes to fit the question. Aim for 3-6.)

## 3. Where they agree

Often overlooked: where do {{X}} and {{Y}} *not* differ meaningfully? Acknowledging this prevents the report from inventing conflicts.

## 4. Where they disagree (and why)

For each meaningful disagreement, name:
- The empirical observation
- The methodological reason (different datasets, baselines, hyperparameters)
- The theoretical reason (different framings)

## 5. Overall recommendation

If the user must pick one today, with no further information:

- Pick **{{X}}** when {{conditions}}
- Pick **{{Y}}** when {{conditions}}
- Pick **neither** (or wait) when {{conditions}}

## 6. Open questions

What would change the verdict? What study would be most informative?

## Appendix A — Methodology

{{search + ranking + dedupe stats}}

## Appendix B — Self-critique

{{self_critique.appendix}}

## Bibliography

{{rendered from export_bibtex.py}}
