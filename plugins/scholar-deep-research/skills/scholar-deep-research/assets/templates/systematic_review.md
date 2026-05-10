# {{title}}: A Systematic Review

**Question (PICO):**
- **Population:** {{P}}
- **Intervention:** {{I}}
- **Comparator:** {{C}}
- **Outcome:** {{O}}

**Date:** {{date}}
**Protocol:** This review followed PRISMA-lite guidance. Search and screening were not pre-registered.

---

## 1. Background and rationale

Why does this question matter? What is the prior state of evidence?

## 2. Methods

### 2.1 Search strategy

| Source | Query | Date searched | Hits | Included |
|--------|-------|---------------|------|----------|
| OpenAlex | `{{cluster A}}` | {{date}} | {{n}} | {{n}} |
| PubMed | `{{cluster A}}` | {{date}} | {{n}} | {{n}} |
| arXiv | `{{cluster B}}` | {{date}} | {{n}} | {{n}} |
| Crossref | `{{cluster C}}` | {{date}} | {{n}} | {{n}} |
| Citation chase | seeds={{n}}, depth=1 | {{date}} | {{n}} | {{n}} |

### 2.2 Inclusion criteria

- {{criterion 1}}
- {{criterion 2}}
- {{criterion 3}}

### 2.3 Exclusion criteria

- {{criterion 1}}
- {{criterion 2}}

### 2.4 Risk-of-bias assessment

For each included study we noted: sample size, pre-registration status, blinding, conflicts of interest, retraction status, and replication status. See extraction table.

## 3. PRISMA-lite flow

```
Records identified: {{total_hits}}
        │
        ▼
After dedupe: {{after_dedupe}}
        │
        ▼
Screened (title/abstract): {{after_screen}}
        │
        ▼
Full-text assessed: {{full_text}}
        │
        ├── Excluded ({{n}}):
        │     - {{reason 1}}: n={{n}}
        │     - {{reason 2}}: n={{n}}
        ▼
Included in synthesis: {{included}}
```

## 4. Extraction table

| Study | Year | n | Population | Intervention | Comparator | Outcome | Effect | Risk of bias |
|-------|------|---|------------|--------------|------------|---------|--------|--------------|
| [^id1] | {{y}} | {{n}} | ... | ... | ... | ... | ... | low/med/high |
| [^id2] | ... | ... | ... | ... | ... | ... | ... | ... |

## 5. Synthesis

### 5.1 Primary outcome
Narrative synthesis. If outcomes are numerical and homogeneous, a meta-analytic note can go here (the skill does not run meta-analyses — flag this for the user).

### 5.2 Secondary outcomes

### 5.3 Subgroup observations

## 6. Quality of evidence

Use a GRADE-style summary if applicable, otherwise narrative:

- **High:** {{summary}}
- **Moderate:** {{summary}}
- **Low / very low:** {{summary}}

## 7. Conclusions

What does the body of evidence support, with what confidence?

## 8. Limitations of this review

- {{limitation 1}}
- {{limitation 2}}
- {{from self-critique appendix}}

## Appendix A — Methodology details

(See SKILL.md Phase 0-7 description; same content as literature_review template.)

## Appendix B — Self-critique

{{self_critique.appendix}}

## Bibliography

{{rendered from export_bibtex.py}}
