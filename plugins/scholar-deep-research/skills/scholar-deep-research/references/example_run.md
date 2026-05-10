# Example run

A complete walk-through showing what the 8-phase workflow looks like end-to-end on a single concrete question. Useful as a sanity check that your own run is hitting the expected checkpoints.

```
User: Give me a deep research report on CRISPR base editing for Duchenne muscular dystrophy.

Agent:
[Phase 0] Restating: "What is the current state and evidence for CRISPR base editing
          as a therapeutic approach for Duchenne muscular dystrophy (DMD)?"
          Archetype: literature_review (default; confirmed — broad overview requested)
          Clusters:
            - ("base editing" OR "adenine base editor" OR "cytosine base editor" OR ABE OR CBE)
            - ("Duchenne muscular dystrophy" OR DMD OR dystrophin)
            - (in vivo OR AAV OR "muscle delivery")
          → research_state.json initialized

[Phase 1] Running OpenAlex + PubMed + arXiv + Crossref across 3 clusters...
          Round 1: 187 hits, 142 unique. Round 2: 94 hits, 31 new.
          Saturation check: new=11%, max_new_citations=23 → SATURATED
          143 unique papers in state.

[Phase 2] Ranking with default weights (literature review)...
          Top 20 selected. Score components written to state.
          Triage: 10 deep / 10 skim. Prefetch fills 9/10 deep PDFs (1 paywalled,
          surfaced to user via --emit-manifest manifest).

[Phase 3] Fetching full text... 17/20 full, 3 abstract-only (flagged shallow).
          Evidence extraction complete.

[Phase 4] Citation chasing on top 8 seeds, depth 1.
          OpenAlex + S2 backends both run. Added 24 candidates after dedupe,
          6 re-scored into top 20.

[Phase 5] Themes: (a) delivery platforms, (b) editing efficiency, (c) off-target/safety,
          (d) pre-clinical outcomes, (e) clinical translation barriers.
          Tensions: AAV serotype optimality (Theme a) — 3 papers disagree.

[Phase 6] Self-critique flagged 2 single-source claims and a recency gap
          (no 2025 paper in top 20). Re-ran focused search; added 4 papers.

[Phase 7] Rendering literature_review template...
          Report: reports/crispr-base-editing-dmd_20260411.md
          Bibliography: reports/crispr-base-editing-dmd_20260411.bib (84 refs)
```

## Things to notice

- **Phase 1 took two rounds, not one.** Saturation isn't a single search — 11% new on round 2 is what passed the threshold.
- **Phase 2 split into deep/skim** before fan-out, with a paywall manifest surfaced to the user. The agent did not waste an agent dispatch on the paywalled paper.
- **Phase 4 ran both OpenAlex and S2** by default, then deduped — coverage gaps between the two are real, especially for CS-adjacent biomed.
- **Phase 6 found a recency gap** and looped back to search before declaring done. Self-critique is not a checkbox; it's allowed to push the workflow backwards.
- **Final bibliography size (84) > top-N (20)**: every paper anchored in the report's appendices/methodology — including ones from the citation chase that weren't in the top-20 deep-read pool — gets a bibliography entry.
