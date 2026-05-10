# {{title}}: A Scoping Review

**Question:** What has been studied (and how) in {{topic}}?
**Date:** {{date}}
**Sources consulted:** {{sources}}
**Papers in corpus:** {{total_papers}}

---

## 1. Background

Why scope this field? Who is the audience? What does the user need to plan next?

## 2. Scope question

Refined scope statement (broader than a PICO; narrow enough to be tractable).

## 3. Methods

Brief — scoping reviews use broad inclusion. Note minimum exclusion criteria only.

| Source | Cluster | Hits | Included |
|--------|---------|------|----------|
| OpenAlex | {{...}} | {{n}} | {{n}} |

## 4. Coverage map

A matrix view of the field. Rows = subtopics, columns = methods (or populations, or settings). Cell = paper count.

| Subtopic ↓ / Method → | Method A | Method B | Method C | Method D |
|-----------------------|----------|----------|----------|----------|
| Subtopic 1 | n=12 | n=4 | — | n=1 |
| Subtopic 2 | n=2 | n=18 | n=6 | — |
| Subtopic 3 | — | — | n=3 | n=14 |

The empty cells are the gap.

## 5. Methods inventory

What methods has the field used? Brief description of each, with a representative paper.

- **Method A:** {{description}}. Representative: [^id]
- **Method B:** {{description}}. Representative: [^id]

## 6. Population / setting inventory

Same shape — what populations, models, or settings have been studied?

## 7. Subtopic narratives

One short paragraph per subtopic, with anchor pointers to the most representative work — *not* a full review of each.

### 7.1 {{Subtopic 1}}
{{paragraph with anchors}}

### 7.2 {{Subtopic 2}}
{{paragraph with anchors}}

## 8. Research gap

Synthesize the empty cells into a research gap statement. This is the deliverable.

- **Gap 1:** {{description}}
- **Gap 2:** {{description}}
- **Gap 3:** {{description}}

## 9. Recommendations for future work

- Most tractable next study: {{...}}
- Highest-impact next study: {{...}}
- Methodological recommendation: {{...}}

## Appendix A — Methodology

{{search + ranking + dedupe stats}}

## Appendix B — Self-critique

{{self_critique.appendix}}

## Bibliography

{{rendered from export_bibtex.py}}
