# Search Strategies

Reference for Phase 1 (Discovery) and Phase 4 (Citation chasing). Load this when planning queries or when discovery feels unproductive.

## Boolean clusters

A query is rarely a single keyword. Build 3-5 *clusters* of synonyms and join them with AND. Example for "CRISPR base editing for muscular dystrophy":

```
Cluster A (technique): "base editing" OR "adenine base editor" OR ABE OR
                       "cytosine base editor" OR CBE OR prime editing
Cluster B (disease):   "Duchenne muscular dystrophy" OR DMD OR
                       "Becker muscular dystrophy" OR dystrophinopathy OR
                       dystrophin
Cluster C (delivery):  AAV OR "adeno-associated virus" OR LNP OR
                       "lipid nanoparticle" OR "in vivo delivery"
Negative:              NOT review NOT editorial NOT comment
```

Each search script accepts one query at a time — run one cluster per call, then dedupe across all of them. Don't pre-AND clusters; that over-constrains and misses cross-references.

## PICO (or PICO-style)

For comparative or systematic questions, decompose with PICO:

| Letter | What |
|--------|------|
| P | Population, problem, or phenomenon |
| I | Intervention or independent variable |
| C | Comparator (often baseline or alternative) |
| O | Outcome — what is measured |

Non-biomedical translations:
- ML: Task, Method, Baseline, Metric (TMBM)
- Engineering: System, Modification, Reference, Performance
- Social science: Population, Treatment, Control, Effect

PICO matters because it forces you to articulate what counts as an answer — and that constrains your search.

## Snowballing

Two flavors. Both are run by `build_citation_graph.py`:

- **Backward snowballing.** Pull the references of high-quality seed papers. The best work cites foundational papers you'd otherwise miss with keywords.
- **Forward snowballing.** Pull the cited-by list. The most recent critiques, replications, and extensions live here.

**Special case — citation chasing for criticism.** When a paper has very high citations but no critique appears in your corpus, search explicitly:

```
"<first author> <year>" (critique OR limitations OR reanalysis OR
                          replication OR failed OR flawed OR overstated)
```

If no critique exists, that's interesting. Note it. Don't assume "uncriticized" = "correct."

## Saturation

Discovery ends when *adding more search rounds stops adding signal*, not when you get tired. The script `research_state.py saturation` formalizes this:

```
saturated when:
  (new_papers_in_round / total_in_round) < 20%   AND
  max(citations of papers first seen in round) < 100
```

The first condition catches "we've seen most of these before." The second catches "but there's still a high-impact paper we missed." Both must hold.

If one cluster saturates and another doesn't, run more rounds on the unsaturated cluster only.

## Iteration patterns

A productive search sequence usually looks like:

```
Round 1: broad keywords on each cluster, limit=50
Round 2: tighter keywords (using terms learned from Round 1 abstracts)
Round 3: author search for repeat-appearing authors (search by author name)
Round 4: citation chase (build_citation_graph) on top 8 seeds
Round 5: targeted gap fills based on Phase 6 self-critique
```

**A keyword you didn't know existed yesterday but appears in 6 abstracts today is a signal.** Re-run Round 1 with that keyword added to the cluster.

## Source-specific tips

- **OpenAlex** is the best general-purpose first stop. Free, no key, citation counts included.
- **arXiv** for CS/ML/physics preprints. Note: papers are unrefereed until cross-listed with a venue.
- **Crossref** is best for *known DOIs* — verify metadata, find venue, get bibliographic detail.
- **PubMed** for biomedical questions. Use MeSH terms when you know them: `"CRISPR-Cas Systems"[MeSH]`.

## Common failure modes

- **First-page fixation.** The first 10 OpenAlex results aren't "the literature." Run multiple rounds and chase citations.
- **Acronym blindness.** "ABE" means base editor, but also "average bit error" — disambiguate with co-occurring terms.
- **English-only.** Some fields have important non-English literature. Note this in the report's limitations.
- **Recency collapse.** Saturation can fire before the most recent year is well-covered. Always run a final query restricted to the last 18 months.
