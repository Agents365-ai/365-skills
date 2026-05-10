"""Phase-advance gate predicates for scholar-deep-research.

Each gate G_N returns a `GateResult` when asked "can we advance TO phase N?".
A gate answers with a list of `Check` records so the envelope surfaces the
entire checklist — pass or fail — and not just a boolean. The host LLM uses
this to understand *why* a gate failed (or passed) rather than re-deriving.

Some criteria (like "≥3 keyword clusters" in G1) cannot be mechanically
verified from state; those checks are declared with `host_checked=True` and
always return ok=True with an explanatory `detail`. Honest acknowledgment
beats a lie.

Gates correspond to SKILL.md's "Completion gates" table. The numeric key is
the TARGET phase: `GATES[3]` validates "can we advance from phase 2 to
phase 3?".
"""
from __future__ import annotations

from typing import Any, Callable, NamedTuple


class Check(NamedTuple):
    name: str
    ok: bool
    detail: str
    host_checked: bool = False


class GateResult(NamedTuple):
    target: int
    checks: list[Check]

    @property
    def met(self) -> bool:
        return all(c.ok for c in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "met": self.met,
            "checks": [
                {"name": c.name, "ok": c.ok, "detail": c.detail,
                 "host_checked": c.host_checked}
                for c in self.checks
            ],
        }


_VALID_ARCHETYPES = {
    "literature_review", "systematic_review", "scoping_review",
    "comparative_analysis", "grant_background",
}


def _phase_is(state: dict[str, Any], want: int) -> Check:
    have = state.get("phase", -1)
    return Check(
        name="phase_current",
        ok=have == want,
        detail=f"current phase={have}, expected {want}",
    )


def _distinct_sources(state: dict[str, Any]) -> set[str]:
    return {q.get("source") for q in state.get("queries", []) if q.get("source")}


def gate_1(state: dict[str, Any]) -> GateResult:
    """0 → 1: Question restated, archetype chosen, state initialized."""
    checks: list[Check] = [
        _phase_is(state, 0),
        Check(
            name="question_set",
            ok=bool(state.get("question")),
            detail=f"state.question length={len(state.get('question') or '')}",
        ),
        Check(
            name="archetype_valid",
            ok=state.get("archetype") in _VALID_ARCHETYPES,
            detail=f"state.archetype={state.get('archetype')!r} "
                   f"(valid: {sorted(_VALID_ARCHETYPES)})",
        ),
        Check(
            name="state_initialized",
            ok="papers" in state and "queries" in state,
            detail="papers and queries keys present",
        ),
        Check(
            name="keyword_clusters_covered",
            ok=True,
            detail="SKILL.md requires ≥3 keyword clusters — not mechanically "
                   "verifiable from state. Host LLM confirms during Phase 0.",
            host_checked=True,
        ),
    ]
    return GateResult(target=1, checks=checks)


def gate_2(state: dict[str, Any],
           *, compute_saturation: Callable[[dict[str, Any]], dict[str, Any]]) -> GateResult:
    """1 → 2: Saturation on all queried sources AND ≥3 sources consulted."""
    sources = _distinct_sources(state)
    try:
        sat = compute_saturation(state)
        overall = bool(sat.get("overall_saturated"))
        sat_detail = f"per_source={list(sat.get('per_source', {}).keys())}"
    except Exception as exc:
        # compute_saturation raises SaturationInputError when no queries
        # exist; treat that as "not yet saturated" without killing the
        # process. Any other exception is unexpected — re-raise so it
        # surfaces in the envelope rather than being silently swallowed.
        if type(exc).__name__ != "SaturationInputError":
            raise
        overall = False
        sat_detail = str(exc)

    checks = [
        _phase_is(state, 1),
        Check(
            name="sources_breadth",
            ok=len(sources) >= 3,
            detail=f"distinct sources queried: {sorted(sources)} "
                   f"({len(sources)} of required 3)",
        ),
        Check(
            name="saturation_overall",
            ok=overall,
            detail=sat_detail,
        ),
    ]
    return GateResult(target=2, checks=checks)


def gate_3(state: dict[str, Any]) -> GateResult:
    """2 → 3: Top-N selected, scored, and triaged into deep/skim/defer tiers."""
    selected = state.get("selected_ids") or []
    papers = state.get("papers") or {}
    with_components = [
        pid for pid in selected
        if isinstance(papers.get(pid), dict)
        and papers[pid].get("score_components")
    ]
    checks = [
        _phase_is(state, 2),
        Check(
            name="ranking_recorded",
            ok=bool(state.get("ranking")),
            detail=f"state.ranking set = {bool(state.get('ranking'))}",
        ),
        Check(
            name="selection_non_empty",
            ok=len(selected) > 0,
            detail=f"selected_ids count = {len(selected)}",
        ),
        Check(
            name="selected_have_score_components",
            ok=(len(selected) > 0 and len(with_components) == len(selected)),
            detail=f"{len(with_components)} / {len(selected)} selected papers "
                   f"have score_components",
        ),
        Check(
            name="triage_applied",
            ok=bool(state.get("triage_complete")),
            detail=f"state.triage_complete = {state.get('triage_complete')!r}; "
                   f"run skim_papers.py before advancing to Phase 3 so the "
                   f"deep/skim/defer tiers are assigned and selected_ids "
                   f"refined to the deep+skim slice.",
        ),
    ]
    return GateResult(target=3, checks=checks)


def gate_4(state: dict[str, Any]) -> GateResult:
    """3 → 4: every deep-tier paper has been deep-read (depth='full').

    With triage (G3) the gate is tier-aware: skim-tier papers are
    intentionally `depth='shallow'` (abstract-only evidence stub written by
    `apply_triage`), so the legacy "≥80% of selected are full" rule no
    longer carries semantic weight. The new bar is sharper: every paper
    the agent committed to deep-read (`tier='deep'`) must have an
    agent-written full evidence record (`depth='full'`). Skim-tier
    incompleteness can never block this gate; only an unfinished agent
    fan-out can.

    Failure-mode escape hatch: when a deep-tier paper's full text is
    genuinely unreachable (paywall, OA chain exhausted, scanned PDF), the
    Phase 3 agent prompt instructs the agent to write
    `depth='shallow'` plus `evidence.method='evidence_unavailable: <code>'`.
    Such records count toward deep-tier coverage (the agent committed and
    explicitly recorded the failure) — otherwise a single unreachable PDF
    would block the entire workflow forever.
    """
    selected = state.get("selected_ids") or []
    papers = state.get("papers") or {}
    depths = [(papers.get(pid) or {}).get("depth") for pid in selected]
    valid_depth = all(d in ("full", "shallow") for d in depths)

    deep_ids = [pid for pid in selected
                if (papers.get(pid) or {}).get("tier") == "deep"]
    deep_full: list[str] = []
    deep_unavailable: list[str] = []
    for pid in deep_ids:
        p = papers.get(pid) or {}
        if p.get("depth") == "full":
            deep_full.append(pid)
            continue
        # Accept depth=shallow when the agent explicitly recorded an
        # evidence_unavailable failure — the deep-read attempt happened,
        # the source was unreachable, the failure is auditable.
        method = ((p.get("evidence") or {}).get("method") or "")
        if (p.get("depth") == "shallow"
                and method.startswith("evidence_unavailable:")):
            deep_unavailable.append(pid)

    deep_covered = len(deep_full) + len(deep_unavailable)
    # Vacuous truth when deep tier is empty (e.g. user ran with
    # --deep-ratio 0.0). The skill still ships, just with no agent-grade
    # evidence — that is a deliberate user choice.
    deep_complete = deep_covered == len(deep_ids)

    coverage_detail = (
        f"{len(deep_full)} / {len(deep_ids)} deep-tier papers have "
        f"depth='full'"
    )
    if deep_unavailable:
        coverage_detail += (
            f"; {len(deep_unavailable)} additional accepted as "
            f"depth='shallow' with method^='evidence_unavailable:' "
            f"(unreachable source, failure recorded)"
        )
    coverage_detail += " (skim-tier excluded; depth='shallow' is by design)"

    checks = [
        _phase_is(state, 3),
        Check(
            name="depth_marks_valid",
            ok=valid_depth,
            detail="every selected paper has depth in {'full','shallow'} "
                   f"(bad: {[d for d in depths if d not in ('full','shallow')]})",
        ),
        Check(
            name="deep_tier_full_evidence",
            ok=deep_complete,
            detail=coverage_detail,
        ),
    ]
    return GateResult(target=4, checks=checks)


def gate_5(state: dict[str, Any]) -> GateResult:
    """4 → 5: Citation graph expanded on seeds (≥1 chase query with hits > 0)."""
    chase_queries = [
        q for q in state.get("queries", [])
        if q.get("source") == "openalex_citation_chase"
    ]
    with_hits = [q for q in chase_queries if (q.get("hits") or 0) > 0]
    checks = [
        _phase_is(state, 4),
        Check(
            name="citation_chase_run",
            ok=len(chase_queries) > 0,
            detail=f"openalex_citation_chase queries: {len(chase_queries)}",
        ),
        Check(
            name="citation_chase_productive",
            ok=len(with_hits) > 0,
            detail=f"chase queries with hits > 0: {len(with_hits)}",
        ),
    ]
    return GateResult(target=5, checks=checks)


def gate_6(state: dict[str, Any]) -> GateResult:
    """5 → 6: ≥3 themes AND (≥1 tension OR explicit no-tensions finding)."""
    themes = state.get("themes") or []
    tensions = state.get("tensions") or []
    crit_findings = (state.get("self_critique") or {}).get("findings") or []
    no_tensions_ack = any(
        "no tension" in (f or "").lower() or "no_tensions" in (f or "").lower()
        for f in crit_findings
    )
    checks = [
        _phase_is(state, 5),
        Check(
            name="themes_defined",
            ok=len(themes) >= 3,
            detail=f"themes: {len(themes)} of required 3",
        ),
        Check(
            name="tensions_or_acknowledgment",
            ok=len(tensions) >= 1 or no_tensions_ack,
            detail=(f"tensions={len(tensions)}; "
                    f"no_tensions_ack={no_tensions_ack}"),
        ),
    ]
    return GateResult(target=6, checks=checks)


def gate_7(state: dict[str, Any]) -> GateResult:
    """6 → 7: Self-critique appendix written, findings all resolved."""
    crit = state.get("self_critique") or {}
    appendix = crit.get("appendix") or ""
    findings = crit.get("findings") or []
    resolved = crit.get("resolved") or []
    # A finding is considered resolved if the count of resolved entries is
    # at least the count of findings. Pairing is host-directed; we only
    # enforce the cardinality.
    all_resolved = len(resolved) >= len(findings)
    checks = [
        _phase_is(state, 6),
        Check(
            name="critique_appendix_written",
            ok=bool(appendix.strip()),
            detail=f"appendix length = {len(appendix)}",
        ),
        Check(
            name="findings_resolved",
            ok=all_resolved,
            detail=f"resolved ({len(resolved)}) >= findings ({len(findings)})",
        ),
    ]
    return GateResult(target=7, checks=checks)


GATES: dict[int, Callable[..., GateResult]] = {
    1: gate_1,
    2: gate_2,
    3: gate_3,
    4: gate_4,
    5: gate_5,
    6: gate_6,
    7: gate_7,
}


# Per-check remediation hints. When a gate fails, cmd_advance looks up each
# failing check's name in this table and surfaces the listed commands under
# the envelope's `next` slot, per the skill's "reducing agent round-trips"
# guidance. Hints are generic shell snippets; the advance handler fills in
# the state path so the host LLM can copy-paste or pipe.
#
# Add more hints as gates are refined. Unknown check names silently yield
# no hint — failure is still visible in the `checks` list.
_NEXT_HINTS: dict[str, list[str]] = {
    # G1
    "question_set": [
        "python scripts/research_state.py --state {state} init "
        "--question '...' --archetype literature_review",
    ],
    "archetype_valid": [
        "python scripts/research_state.py --state {state} set "
        "--field archetype --value '\"literature_review\"'",
    ],
    "state_initialized": [
        "python scripts/research_state.py --state {state} init "
        "--question '...' --archetype literature_review --force --dangerous",
    ],
    # G2
    "sources_breadth": [
        "python scripts/search_arxiv.py --query '...' --state {state} --round N",
        "python scripts/search_crossref.py --query '...' --state {state} --round N",
        "python scripts/search_pubmed.py --query '...' --state {state} --round N",
        "python scripts/search_dblp.py --query '...' --state {state} --round N",
        "python scripts/search_biorxiv.py --query '...' --state {state} --round N",
        "python scripts/search_exa.py --query '...' --state {state} --round N",
    ],
    "saturation_overall": [
        "python scripts/search_openalex.py --query '<next cluster>' --state {state} --round N",
        "python scripts/research_state.py --state {state} saturation",
    ],
    # G3
    "ranking_recorded": [
        "python scripts/rank_papers.py --state {state}",
    ],
    "selection_non_empty": [
        "python scripts/research_state.py --state {state} select --top 20",
    ],
    "selected_have_score_components": [
        "python scripts/rank_papers.py --state {state}",
    ],
    "triage_applied": [
        "python scripts/skim_papers.py --state {state} "
        "--deep-ratio 0.5 --skim-ratio 0.5",
    ],
    # G4
    "deep_tier_full_evidence": [
        "# Dispatch parallel agents per references/agent_prompts/phase3_deep_read.md",
        "python scripts/extract_pdf.py --doi '<doi>' --output paper.txt",
        "python scripts/research_state.py --state {state} evidence "
        "--id '<paper_id>' --method '...' --depth full",
    ],
    "depth_marks_valid": [
        "python scripts/research_state.py --state {state} evidence "
        "--id '<paper_id>' --method '...' --depth shallow",
    ],
    # G5
    "citation_chase_run": [
        "python scripts/build_citation_graph.py --state {state} "
        "--seed-top 5 --direction both",
    ],
    "citation_chase_productive": [
        "python scripts/build_citation_graph.py --state {state} "
        "--seed-top 8 --direction both --cited-by-limit 100",
    ],
    # G6
    "themes_defined": [
        "python scripts/research_state.py --state {state} theme "
        "--name '<theme>' --summary '...' --paper-ids ...",
    ],
    "tensions_or_acknowledgment": [
        "python scripts/research_state.py --state {state} tension "
        "--topic '<topic>' --sides '[{\"position\": \"...\", \"paper_ids\": [...]}, ...]'",
        "python scripts/research_state.py --state {state} critique "
        "--finding 'no_tensions: <reason>'",
    ],
    # G7
    "critique_appendix_written": [
        "python scripts/research_state.py --state {state} critique "
        "--appendix '<adversarial review text>'",
    ],
    "findings_resolved": [
        "python scripts/research_state.py --state {state} critique "
        "--resolve '<how each finding was addressed>'",
    ],
}


def next_hints_for(checks: list[Check], state_path: str) -> list[str]:
    """Suggested follow-up commands for the failing checks in `checks`.

    The host LLM can read this directly off the envelope and does not need
    a separate discovery turn to work out what to do next. Placeholders
    like `'...'` and `<topic>` are intentional — the agent fills them in
    from its own reasoning; we only know the shape of the command.
    """
    out: list[str] = []
    seen: set[str] = set()
    for c in checks:
        if c.ok:
            continue
        for hint in _NEXT_HINTS.get(c.name, []):
            # Plain .replace rather than .format so literal `{...}` in JSON
            # argument snippets (e.g. the tension --sides example) doesn't
            # collide with str.format's placeholder syntax.
            cmd = hint.replace("{state}", state_path)
            if cmd not in seen:
                out.append(cmd)
                seen.add(cmd)
    return out
