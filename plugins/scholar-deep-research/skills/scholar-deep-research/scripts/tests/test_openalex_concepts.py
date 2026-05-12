"""F2 — OpenAlex concepts flow end-to-end to ranker top-N output.

Background: the keyword-only relevance scorer pulls high-citation
papers from adjacent domains (CRISPR/cancer in an AAV query, vision
Mamba derivatives in a Mamba/Transformer query) into the top-N because
surface tokens match without semantic discrimination. The 0.17.0 fix
preserves OpenAlex `concepts` on each paper and surfaces them in the
ranker `top` output so the host LLM can spot cluster skew before triage.

These tests pin:
  - _normalize extracts top-3 concepts by score, drops level-0 roots,
    rounds scores to 3 decimals
  - papers without concepts get no `concepts` key (make_paper drops None)
  - rank_papers includes `concepts` in every preview entry
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

# Make scripts/ importable
SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS))

import search_openalex  # noqa: E402
from tests._helpers import init_state, run_script  # noqa: E402


class NormalizeConceptsTest(unittest.TestCase):
    def test_top_3_by_score_kept(self) -> None:
        work = {
            "id": "https://openalex.org/W1",
            "title": "Test",
            "concepts": [
                {"display_name": "A", "level": 2, "score": 0.9},
                {"display_name": "B", "level": 3, "score": 0.8},
                {"display_name": "C", "level": 2, "score": 0.7},
                {"display_name": "D", "level": 1, "score": 0.6},
            ],
        }
        p = search_openalex._normalize(work)
        names = [c["name"] for c in p["concepts"]]
        self.assertEqual(names, ["A", "B", "C"])

    def test_level_zero_filtered_out(self) -> None:
        """Level-0 concepts ('Biology', 'Computer science') match every
        paper in a field and would dilute the cluster signal."""
        work = {
            "id": "https://openalex.org/W2",
            "title": "Test",
            "concepts": [
                {"display_name": "Biology", "level": 0, "score": 0.99},
                {"display_name": "Specific topic", "level": 3, "score": 0.5},
            ],
        }
        p = search_openalex._normalize(work)
        names = [c["name"] for c in p["concepts"]]
        self.assertEqual(names, ["Specific topic"])
        self.assertNotIn("Biology", names)

    def test_scores_rounded_to_3_decimals(self) -> None:
        work = {
            "id": "https://openalex.org/W3",
            "title": "Test",
            "concepts": [{"display_name": "X", "level": 2, "score": 0.123456789}],
        }
        p = search_openalex._normalize(work)
        self.assertEqual(p["concepts"][0]["score"], 0.123)

    def test_no_concepts_returns_none_so_field_is_absent(self) -> None:
        """make_paper drops keys whose value is None — keeping concepts=None
        means the field is absent on papers from non-OpenAlex sources,
        which is what the rank_papers preview falls back to with .get()."""
        work = {"id": "https://openalex.org/W4", "title": "Test", "concepts": []}
        p = search_openalex._normalize(work)
        self.assertNotIn("concepts", p)

    def test_concepts_without_display_name_skipped(self) -> None:
        """Defensive: OpenAlex occasionally returns concept records with
        missing display_name; those should be dropped, not crash."""
        work = {
            "id": "https://openalex.org/W5",
            "title": "Test",
            "concepts": [
                {"display_name": None, "level": 2, "score": 0.9},
                {"display_name": "Real", "level": 2, "score": 0.7},
            ],
        }
        p = search_openalex._normalize(work)
        self.assertEqual([c["name"] for c in p["concepts"]], ["Real"])


class RankerSurfacesConceptsTest(unittest.TestCase):
    """End-to-end via subprocess: ingest two papers (one with concepts,
    one without), run rank_papers --dry-run, assert top preserves the field."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="f2_test_"))
        self.state_path = self.tmp / "state.json"
        init_state(self.state_path, question="test", archetype="literature_review")
        # Ingest a payload with one concept-bearing paper and one without
        import json as _json
        payload = {
            "source": "openalex",
            "query": "test",
            "round": 1,
            "papers": [
                {
                    "doi": "10.1234/with-concepts",
                    "title": "Paper with concepts",
                    "authors": ["A"], "year": 2024,
                    "venue": "Nature", "abstract": "test test",
                    "citations": 100, "url": None, "pdf_url": None,
                    "concepts": [{"name": "Genome editing",
                                  "level": 3, "score": 0.9}],
                },
                {
                    "doi": "10.1234/no-concepts",
                    "title": "Paper without concepts",
                    "authors": ["B"], "year": 2023,
                    "venue": "Cell", "abstract": "test test",
                    "citations": 50, "url": None, "pdf_url": None,
                },
            ],
        }
        payload_path = self.tmp / "payload.json"
        payload_path.write_text(_json.dumps(payload))
        envelope = run_script("research_state.py", [
            "--state", str(self.state_path), "ingest",
            "--input", str(payload_path),
        ])
        assert envelope.get("ok"), envelope

    def test_rank_top_includes_concepts_field_for_both(self) -> None:
        envelope = run_script("rank_papers.py", [
            "--state", str(self.state_path),
            "--dry-run",
            "--top", "10",
        ])
        self.assertTrue(envelope["ok"], envelope)
        top = envelope["data"]["top"]
        by_id = {p["id"]: p for p in top}

        with_id = "doi:10.1234/with-concepts"
        no_id = "doi:10.1234/no-concepts"
        self.assertIn(with_id, by_id)
        self.assertIn(no_id, by_id)

        # Paper with concepts: surfaces them
        self.assertEqual(
            by_id[with_id]["concepts"],
            [{"name": "Genome editing", "level": 3, "score": 0.9}],
        )
        # Paper without concepts: field present, value None
        self.assertIn("concepts", by_id[no_id])
        self.assertIsNone(by_id[no_id]["concepts"])


if __name__ == "__main__":
    unittest.main()
