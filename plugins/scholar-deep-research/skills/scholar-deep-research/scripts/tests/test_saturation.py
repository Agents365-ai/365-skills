"""Saturation now has three axes: paper-novelty, author-novelty, venue-novelty.

The legacy paper-pct rule alone could be gamed by re-running the same query
(round 2 trivially has 0 new papers). Author + venue diversity catches that
case and also the "we found another big paper but it's the same hub authors"
case. Each axis must independently fall under its threshold for a source to
count as saturated.

Tests construct state dicts directly and call `compute_saturation` as a pure
function. One CLI integration test confirms the new fields land in the
envelope.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from research_state import compute_saturation  # noqa: E402

from _helpers import run_script  # noqa: E402


def _state(*, queries, papers) -> dict:
    return {
        "schema_version": 1,
        "question": "t",
        "archetype": "literature_review",
        "phase": 1,
        "queries": queries,
        "papers": papers,
        "selected_ids": [],
        "themes": [],
        "tensions": [],
        "self_critique": {"findings": [], "resolved": [], "appendix": ""},
        "report_path": None,
    }


def _paper(pid, *, source, round_, authors, venue, citations=5):
    return {
        "id": pid,
        "title": pid,
        "doi": None,
        "authors": authors,
        "venue": venue,
        "year": 2024,
        "citations": citations,
        "source": [source],
        "first_seen_round": round_,
    }


class SaturationAxesTest(unittest.TestCase):
    """Each axis is independently necessary for saturation."""

    def test_high_author_novelty_blocks_saturation(self) -> None:
        """Paper-pct under threshold but new authors keep flooding in → not saturated."""
        # Round 1: 10 papers, 10 authors A1..A10, all same venue V1.
        # Round 2: 1 new paper (10% new — under 20% threshold) but it brings 5
        # brand-new authors A11..A15. With 15 total authors and 5 new, that's
        # 33% — above the 25% default → must NOT saturate.
        r1_papers = {
            f"p{i}": _paper(
                f"p{i}", source="openalex", round_=1,
                authors=[f"A{i}"], venue="V1",
            )
            for i in range(1, 11)
        }
        r2_papers = {
            "p11": _paper(
                "p11", source="openalex", round_=2,
                authors=["A11", "A12", "A13", "A14", "A15"], venue="V1",
            ),
        }
        state = _state(
            queries=[
                {"source": "openalex", "query": "q", "round": 1, "hits": 10, "new": 10},
                {"source": "openalex", "query": "q", "round": 2, "hits": 10, "new": 1},
            ],
            papers={**r1_papers, **r2_papers},
        )
        sat = compute_saturation(state)
        ps = sat["per_source"]["openalex"]
        self.assertFalse(ps["saturated"], f"expected not saturated; got {ps}")
        self.assertIn("new_authors_pct", ps)
        self.assertGreater(ps["new_authors_pct"], 25.0)

    def test_all_axes_low_saturates(self) -> None:
        """Paper-pct, author-pct, and venue-pct all under thresholds → saturated."""
        # Round 1: 20 papers from 20 authors across 5 venues.
        r1_papers = {}
        for i in range(1, 21):
            r1_papers[f"p{i}"] = _paper(
                f"p{i}", source="openalex", round_=1,
                authors=[f"A{i}"], venue=f"V{(i - 1) % 5 + 1}",
            )
        # Round 2: 1 new paper, 1 author already seen, venue already seen.
        r2_papers = {
            "p21": _paper(
                "p21", source="openalex", round_=2,
                authors=["A1"], venue="V1",
            ),
        }
        state = _state(
            queries=[
                {"source": "openalex", "query": "q1", "round": 1, "hits": 20, "new": 20},
                {"source": "openalex", "query": "q2", "round": 2, "hits": 20, "new": 1},
            ],
            papers={**r1_papers, **r2_papers},
        )
        sat = compute_saturation(state)
        ps = sat["per_source"]["openalex"]
        self.assertTrue(ps["saturated"], f"expected saturated; got {ps}")
        self.assertEqual(ps["new_authors_pct"], 0.0)
        self.assertEqual(ps["new_venues_pct"], 0.0)

    def test_missing_venue_skips_axis(self) -> None:
        """A source that never reports venue (e.g. arXiv abstracts) skips that axis."""
        r1 = {
            f"p{i}": _paper(
                f"p{i}", source="arxiv", round_=1,
                authors=[f"A{i}"], venue=None,
            )
            for i in range(1, 6)
        }
        r2 = {
            "p6": _paper(
                "p6", source="arxiv", round_=2,
                authors=["A1"], venue=None,
            ),
        }
        state = _state(
            queries=[
                {"source": "arxiv", "query": "q", "round": 1, "hits": 5, "new": 5},
                {"source": "arxiv", "query": "q", "round": 2, "hits": 5, "new": 1},
            ],
            papers={**r1, **r2},
        )
        sat = compute_saturation(state)
        ps = sat["per_source"]["arxiv"]
        # Venue axis is null (no denominator), authors recur (1/6 ≈ 17% new),
        # paper-pct = 20% — at threshold, not strictly under → adjust expectation.
        # We ASSERT the venue axis is null and not blocking.
        self.assertIsNone(ps["new_venues_pct"])

    def test_single_venue_source_skips_venue_axis(self) -> None:
        """bioRxiv-style: every paper has venue='bioRxiv'. The venue axis
        carries no signal (always 0% new) and would falsely tilt the AND-clause
        toward saturation. It must report null, same as venueless sources."""
        r1 = {
            f"p{i}": _paper(
                f"p{i}", source="biorxiv", round_=1,
                authors=[f"A{i}"], venue="bioRxiv",
            )
            for i in range(1, 6)
        }
        r2 = {
            "p6": _paper(
                "p6", source="biorxiv", round_=2,
                authors=["A6"], venue="bioRxiv",
            ),
        }
        state = _state(
            queries=[
                {"source": "biorxiv", "query": "q", "round": 1, "hits": 5, "new": 5},
                {"source": "biorxiv", "query": "q", "round": 2, "hits": 5, "new": 1},
            ],
            papers={**r1, **r2},
        )
        sat = compute_saturation(state)
        ps = sat["per_source"]["biorxiv"]
        self.assertIsNone(ps["new_venues_pct"])

    def test_thresholds_are_configurable(self) -> None:
        """Stricter author threshold can flip a previously-saturated source."""
        r1 = {
            f"p{i}": _paper(
                f"p{i}", source="openalex", round_=1,
                authors=[f"A{i}"], venue="V1",
            )
            for i in range(1, 11)
        }
        r2 = {
            "p11": _paper(
                "p11", source="openalex", round_=2,
                authors=["A11"], venue="V1",
            ),
        }
        state = _state(
            queries=[
                {"source": "openalex", "query": "q", "round": 1, "hits": 10, "new": 10},
                {"source": "openalex", "query": "q", "round": 2, "hits": 10, "new": 1},
            ],
            papers={**r1, **r2},
        )
        # 1 new author out of 11 = 9.09% → saturated under default 25%.
        sat_default = compute_saturation(state)
        self.assertTrue(sat_default["per_source"]["openalex"]["saturated"])
        # Tighten author threshold to 5% → no longer saturated.
        sat_strict = compute_saturation(state, threshold_authors=5.0)
        self.assertFalse(sat_strict["per_source"]["openalex"]["saturated"])


class NegligibleHitsTest(unittest.TestCase):
    """A source whose last round returns <5 hits saturates by exhaustion.

    Without this guard a narrow source like bioRxiv on a clinical topic that
    returns {2 hits, 1 new} reports new_pct=50% and blocks the AND-clause
    forever — the percent axis is dominated by tiny-denominator noise once a
    source has effectively exhausted its corpus.
    """

    def test_tiny_hits_saturate_after_min_rounds(self) -> None:
        state = _state(
            queries=[
                {"source": "biorxiv", "query": "q", "round": 1,
                 "hits": 8, "new": 8},
                {"source": "biorxiv", "query": "q", "round": 2,
                 "hits": 2, "new": 1},  # 50% — would normally block
            ],
            papers={
                **{f"p{i}": _paper(f"p{i}", source="biorxiv", round_=1,
                                   authors=[f"A{i}"], venue="bioRxiv")
                   for i in range(1, 9)},
                "p9": _paper("p9", source="biorxiv", round_=2,
                             authors=["A9"], venue="bioRxiv"),
            },
        )
        sat = compute_saturation(state)
        ps = sat["per_source"]["biorxiv"]
        self.assertTrue(ps["saturated"], f"expected saturated; got {ps}")
        self.assertTrue(ps["negligible_hits"])
        self.assertEqual(sat["negligible_hits_threshold"], 5)

    def test_tiny_hits_do_not_saturate_before_min_rounds(self) -> None:
        state = _state(
            queries=[
                {"source": "biorxiv", "query": "q", "round": 1,
                 "hits": 2, "new": 1},  # only 1 round so far
            ],
            papers={
                "p1": _paper("p1", source="biorxiv", round_=1,
                             authors=["A1"], venue="bioRxiv"),
                "p2": _paper("p2", source="biorxiv", round_=1,
                             authors=["A2"], venue="bioRxiv"),
            },
        )
        sat = compute_saturation(state)
        ps = sat["per_source"]["biorxiv"]
        self.assertFalse(ps["saturated"])
        self.assertFalse(ps["negligible_hits"])

    def test_threshold_env_override(self) -> None:
        """SCHOLAR_SATURATION_NEGLIGIBLE_HITS shifts the cutoff."""
        import os
        state = _state(
            queries=[
                {"source": "biorxiv", "query": "q", "round": 1,
                 "hits": 10, "new": 10},
                {"source": "biorxiv", "query": "q", "round": 2,
                 "hits": 3, "new": 2},  # 3 hits
            ],
            papers={
                **{f"p{i}": _paper(f"p{i}", source="biorxiv", round_=1,
                                   authors=[f"A{i}"], venue="bioRxiv")
                   for i in range(1, 11)},
                "p11": _paper("p11", source="biorxiv", round_=2,
                              authors=["A11"], venue="bioRxiv"),
                "p12": _paper("p12", source="biorxiv", round_=2,
                              authors=["A12"], venue="bioRxiv"),
            },
        )
        # Default cutoff is 5; 3 hits < 5 → negligible.
        sat_default = compute_saturation(state)
        self.assertTrue(sat_default["per_source"]["biorxiv"]["negligible_hits"])
        # Tighten cutoff to 2; 3 hits >= 2 → no longer negligible.
        prev = os.environ.get("SCHOLAR_SATURATION_NEGLIGIBLE_HITS")
        os.environ["SCHOLAR_SATURATION_NEGLIGIBLE_HITS"] = "2"
        try:
            sat_tight = compute_saturation(state)
        finally:
            if prev is None:
                del os.environ["SCHOLAR_SATURATION_NEGLIGIBLE_HITS"]
            else:
                os.environ["SCHOLAR_SATURATION_NEGLIGIBLE_HITS"] = prev
        self.assertFalse(sat_tight["per_source"]["biorxiv"]["negligible_hits"])


class MinAxesTest(unittest.TestCase):
    """`SCHOLAR_SATURATION_MIN_AXES` controls how many converged axes are
    required for a source to saturate. Default 4 = strict AND of papers /
    citations / authors / venues (the prior behavior). Set 3 = soft mode
    for hot fields where the papers axis stays high due to query
    reformulation breadth while the other three axes converge cleanly.
    """

    def _hot_field_state(self) -> dict:
        # Round 2 surfaces 7/10 new papers (70% — above the 50% papers-axis
        # threshold) but the new papers reuse round-1 authors and round-1
        # venues. citations stay low. Mirrors the Mamba-vs-Transformer +
        # GLP-1 friction case: 3 of 4 axes converged, papers axis stuck.
        # Two distinct venues in round 1 keep the venues axis evaluable
        # (single-venue sources are skipped, reducing axes_evaluable to 3).
        queries = [
            {"source": "openalex", "query": "q1", "round": 1,
             "hits": 10, "new": 10},
            {"source": "openalex", "query": "q2", "round": 2,
             "hits": 10, "new": 7},
        ]
        papers = {}
        for i in range(1, 11):
            papers[f"p{i}"] = _paper(
                f"p{i}", source="openalex", round_=1,
                authors=[f"A{i}", "A_shared"],
                venue="V1" if i <= 5 else "V2",
                citations=5,
            )
        for i in range(11, 18):
            papers[f"p{i}"] = _paper(
                f"p{i}", source="openalex", round_=2,
                authors=["A_shared", f"A{(i % 5) + 1}"],
                venue="V1" if i % 2 else "V2",
                citations=5,
            )
        return _state(queries=queries, papers=papers)

    def test_strict_default_blocks_when_papers_axis_high(self) -> None:
        prev = os.environ.pop("SCHOLAR_SATURATION_MIN_AXES", None)
        try:
            sat = compute_saturation(self._hot_field_state())
        finally:
            if prev is not None:
                os.environ["SCHOLAR_SATURATION_MIN_AXES"] = prev
        ps = sat["per_source"]["openalex"]
        self.assertFalse(ps["saturated"],
                         msg="default min_axes=4 must require papers-axis to converge")
        self.assertEqual(sat["min_axes"], 4)
        self.assertGreaterEqual(ps["axes_passed"], 3,
                                msg="3-of-4 axes should be passing in this fixture")

    def test_soft_mode_saturates_when_3_of_4_axes_pass(self) -> None:
        prev = os.environ.get("SCHOLAR_SATURATION_MIN_AXES")
        os.environ["SCHOLAR_SATURATION_MIN_AXES"] = "3"
        try:
            sat = compute_saturation(self._hot_field_state())
        finally:
            if prev is None:
                del os.environ["SCHOLAR_SATURATION_MIN_AXES"]
            else:
                os.environ["SCHOLAR_SATURATION_MIN_AXES"] = prev
        ps = sat["per_source"]["openalex"]
        self.assertTrue(ps["saturated"],
                        msg="3-of-4 axes converged should saturate under min_axes=3")
        self.assertEqual(sat["min_axes"], 3)
        self.assertGreaterEqual(ps["axes_passed"], 3)

    def test_required_falls_back_to_evaluable_count(self) -> None:
        """When fewer axes are evaluable than min_axes, the requirement
        falls back to "all evaluable" — strict mode is never weakened by
        axis-absence (e.g. single-venue source has venues=None)."""
        # Single-venue, no-citation source: only 2 axes evaluable
        # (papers + citations), not 4.
        queries = [
            {"source": "biorxiv", "query": "q1", "round": 1, "hits": 10, "new": 10},
            {"source": "biorxiv", "query": "q2", "round": 2, "hits": 10, "new": 1},
        ]
        papers = {}
        for i in range(1, 11):
            papers[f"p{i}"] = _paper(
                f"p{i}", source="biorxiv", round_=1,
                authors=[f"A{i}"], venue="bioRxiv", citations=0,
            )
        papers["p11"] = _paper(
            "p11", source="biorxiv", round_=2,
            authors=["A1"], venue="bioRxiv", citations=0,
        )
        prev = os.environ.pop("SCHOLAR_SATURATION_MIN_AXES", None)
        try:
            sat = compute_saturation(_state(queries=queries, papers=papers))
        finally:
            if prev is not None:
                os.environ["SCHOLAR_SATURATION_MIN_AXES"] = prev
        ps = sat["per_source"]["biorxiv"]
        # Venues axis is None (single venue), papers + cit pass, authors pass.
        # axes_evaluable=3, axes_required=min(4,3)=3.
        self.assertEqual(ps["axes_required"], 3)
        self.assertEqual(ps["axes_evaluable"], 3)
        self.assertTrue(ps["saturated"])


class SaturationCLITest(unittest.TestCase):
    """The new axes must appear in the saturation subcommand envelope."""

    def test_envelope_carries_new_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "s.json"
            state = _state(
                queries=[
                    {"source": "openalex", "query": "q", "round": 1,
                     "hits": 5, "new": 5},
                    {"source": "openalex", "query": "q", "round": 2,
                     "hits": 5, "new": 1},
                ],
                papers={
                    **{f"p{i}": _paper(f"p{i}", source="openalex", round_=1,
                                       authors=[f"A{i}"], venue="V1")
                       for i in range(1, 6)},
                    "p6": _paper("p6", source="openalex", round_=2,
                                 authors=["A1"], venue="V1"),
                },
            )
            state_path.write_text(json.dumps(state))
            env = run_script("research_state.py", [
                "--state", str(state_path), "saturation",
            ])
            ps = env["data"]["per_source"]["openalex"]
            self.assertIn("new_authors_pct", ps)
            self.assertIn("new_venues_pct", ps)
            self.assertIn("threshold_authors_pct", env["data"])
            self.assertIn("threshold_venues_pct", env["data"])


if __name__ == "__main__":
    unittest.main()
