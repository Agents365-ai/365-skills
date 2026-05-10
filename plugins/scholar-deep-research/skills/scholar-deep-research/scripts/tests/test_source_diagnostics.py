"""Per-source end-state diagnostics for Phase 1 (item #4 of the Phase 1 backlog).

When a search source fails (HTTP 5xx, timeout, etc.), the failure is
persisted into `state["search_diagnostics"]` so the report-writer in
Phase 7 can footnote "PubMed unavailable; corpus may be biased toward
OpenAlex coverage". Successes are not separately persisted — they are
already implicit in `state["queries"]` and `state["papers"][*].source`.

`compute_source_diagnostics` aggregates everything into a per-source
dict the host LLM can consume directly.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from research_state import (  # noqa: E402
    apply_search_failure, compute_source_diagnostics,
)

from _helpers import dummy_paper, init_state, make_payload, run_script  # noqa: E402


class ApplySearchFailureTest(unittest.TestCase):
    """Direct library-API tests for the failure writer."""

    def test_first_failure_creates_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            init_state(state)
            apply_search_failure(state, "pubmed", "503 from NCBI", status=503)
            doc = json.loads(state.read_text())
            self.assertIn("search_diagnostics", doc)
            self.assertEqual(doc["search_diagnostics"]["pubmed"]["failures"], 1)
            self.assertEqual(doc["search_diagnostics"]["pubmed"]["last_error"]["status"], 503)
            self.assertIn("timestamp", doc["search_diagnostics"]["pubmed"]["last_error"])

    def test_second_failure_overwrites_last_error_and_increments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            init_state(state)
            apply_search_failure(state, "pubmed", "503", status=503)
            apply_search_failure(state, "pubmed", "timeout", status=None)
            doc = json.loads(state.read_text())
            entry = doc["search_diagnostics"]["pubmed"]
            self.assertEqual(entry["failures"], 2)
            self.assertEqual(entry["last_error"]["message"], "timeout")
            self.assertIsNone(entry["last_error"]["status"])

    def test_failures_per_source_independent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            init_state(state)
            apply_search_failure(state, "pubmed", "503", status=503)
            apply_search_failure(state, "openalex", "timeout", status=None)
            doc = json.loads(state.read_text())
            self.assertEqual(doc["search_diagnostics"]["pubmed"]["failures"], 1)
            self.assertEqual(doc["search_diagnostics"]["openalex"]["failures"], 1)


class ComputeSourceDiagnosticsTest(unittest.TestCase):
    """The aggregation helper combines queries + papers + diagnostics."""

    def _state(self, *, queries=None, papers=None, diagnostics=None):
        return {
            "schema_version": 1,
            "question": "t",
            "archetype": "literature_review",
            "phase": 1,
            "queries": queries or [],
            "papers": papers or {},
            "selected_ids": [],
            "themes": [],
            "tensions": [],
            "self_critique": {"findings": [], "resolved": [], "appendix": ""},
            "search_diagnostics": diagnostics or {},
            "report_path": None,
        }

    def test_empty_state_returns_empty_dict(self) -> None:
        diags = compute_source_diagnostics(self._state())
        self.assertEqual(diags, {})

    def test_aggregates_requests_papers_failures(self) -> None:
        state = self._state(
            queries=[
                {"source": "openalex", "query": "q1", "round": 1, "hits": 10, "new": 10},
                {"source": "openalex", "query": "q2", "round": 2, "hits": 5, "new": 1},
                {"source": "arxiv", "query": "q1", "round": 1, "hits": 3, "new": 3},
            ],
            papers={
                "p1": {"id": "p1", "source": ["openalex"]},
                "p2": {"id": "p2", "source": ["openalex", "arxiv"]},
                "p3": {"id": "p3", "source": ["arxiv"]},
            },
            diagnostics={
                "pubmed": {"failures": 2, "last_error": {
                    "message": "503", "status": 503, "timestamp": "2026-05-04T00:00:00+00:00"
                }},
            },
        )
        diags = compute_source_diagnostics(state)
        self.assertEqual(diags["openalex"]["requests"], 2)
        self.assertEqual(diags["openalex"]["papers_contributed"], 2)
        self.assertEqual(diags["openalex"]["failures"], 0)
        self.assertIsNone(diags["openalex"]["last_error"])
        self.assertEqual(diags["arxiv"]["requests"], 1)
        self.assertEqual(diags["arxiv"]["papers_contributed"], 2)
        # PubMed had only failures — no successes, but appears in the report.
        self.assertEqual(diags["pubmed"]["requests"], 0)
        self.assertEqual(diags["pubmed"]["papers_contributed"], 0)
        self.assertEqual(diags["pubmed"]["failures"], 2)
        self.assertEqual(diags["pubmed"]["last_error"]["status"], 503)


class QueryDiagnosticsCLITest(unittest.TestCase):
    """`research_state.py query --what diagnostics` envelope."""

    def test_empty_diagnostics_envelope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            init_state(state)
            env = run_script("research_state.py", [
                "--state", str(state), "query", "diagnostics",
            ])
            self.assertEqual(env["data"], {})

    def test_query_diagnostics_after_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            init_state(state)
            apply_search_failure(state, "pubmed", "503 from NCBI", status=503)
            env = run_script("research_state.py", [
                "--state", str(state), "query", "diagnostics",
            ])
            self.assertIn("pubmed", env["data"])
            self.assertEqual(env["data"]["pubmed"]["failures"], 1)


class SaturationEnrichmentTest(unittest.TestCase):
    """Per-source saturation entries pick up failures + papers_contributed."""

    def test_saturation_envelope_has_diagnostics_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            init_state(state)
            # Push an openalex ingest and a pubmed failure.
            payload = make_payload("openalex", "q", 1, [
                dummy_paper("W1"), dummy_paper("W2"),
            ])
            payload_path = Path(tmp) / "p.json"
            payload_path.write_text(json.dumps(payload))
            run_script("research_state.py", [
                "--state", str(state), "ingest", "--input", str(payload_path),
            ])
            apply_search_failure(state, "pubmed", "503", status=503)
            env = run_script("research_state.py", [
                "--state", str(state), "saturation",
            ])
            ps = env["data"]["per_source"]
            self.assertIn("openalex", ps)
            self.assertEqual(ps["openalex"]["failures"], 0)
            self.assertEqual(ps["openalex"]["papers_contributed"], 2)
            # PubMed had no successful ingest — but failures get surfaced.
            self.assertIn("pubmed", ps)
            self.assertEqual(ps["pubmed"]["failures"], 1)
            self.assertEqual(ps["pubmed"]["papers_contributed"], 0)


if __name__ == "__main__":
    unittest.main()
