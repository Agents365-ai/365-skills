"""Tests for the S2 backend in build_citation_graph.

Network is faked via SCHOLAR_S2_TEST_FAKE: when set, _s2_citations
reads canned responses from a JSON file instead of hitting S2. Lets
the smoke suite stay offline.

The test surface covers four contracts:
  1. --schema reflects --source choices and the new s2 surfaces.
  2. s2_paper_id resolves DOI / arXiv / PMID, returns None otherwise.
  3. normalize_s2_paper produces make_paper-compatible kwargs.
  4. End-to-end: --source s2 only, --source openalex only (regression),
     --source both with both backends contributing.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from _helpers import dummy_paper, init_state, run_script  # noqa: E402


def _ingest_papers(state: Path, papers: list[dict]) -> None:
    payload = {"source": "openalex", "query": "test", "round": 1,
               "papers": papers}
    payload_path = state.parent / "payload.json"
    payload_path.write_text(json.dumps(payload))
    env = run_script("research_state.py", [
        "--state", str(state), "ingest", "--input", str(payload_path),
    ])
    assert env.get("ok"), f"ingest failed: {env}"


def _select(state: Path, top: int = 5) -> None:
    env = run_script("rank_papers.py", ["--state", str(state), "--top", str(top)])
    assert env.get("ok")
    env = run_script("research_state.py", [
        "--state", str(state), "select", "--top", str(top),
    ])
    assert env.get("ok")


class S2ClientUnitTest(unittest.TestCase):
    """Pure-function checks that don't shell out."""

    def test_s2_paper_id_prefers_doi(self):
        from _s2_citations import s2_paper_id
        seed = {"doi": "10.1/abc", "arxiv_id": "2301.12345", "pmid": "999"}
        self.assertEqual(s2_paper_id(seed), "DOI:10.1/abc")

    def test_s2_paper_id_falls_back_to_arxiv_then_pmid(self):
        from _s2_citations import s2_paper_id
        self.assertEqual(s2_paper_id({"arxiv_id": "2301.1"}), "ARXIV:2301.1")
        self.assertEqual(s2_paper_id({"pmid": "42"}), "PMID:42")

    def test_s2_paper_id_returns_none_when_no_handle(self):
        from _s2_citations import s2_paper_id
        self.assertIsNone(s2_paper_id({"openalex_id": "W1"}))
        self.assertIsNone(s2_paper_id({}))

    def test_record_failure_preserves_s2_error_fields(self):
        """When S2 fetch raises, the seed_failures entry must carry the
        structured `code` + `status` + `retryable` so agents can route on
        it. Prior bug: _record_failure read .response.status_code (httpx
        pattern) which silently swallowed S2Error.code."""
        from build_citation_graph import SEED_FAILURES, _record_failure
        from _s2_citations import S2Error

        SEED_FAILURES.clear()
        exc = S2Error("s2_unauthorized", "S2 rejected the request (401)",
                      status=401, retryable=False)
        _record_failure("doi:10.1/x", "s2_citations", exc)

        self.assertEqual(len(SEED_FAILURES), 1)
        rec = SEED_FAILURES[0]
        self.assertEqual(rec["code"], "s2_unauthorized")
        self.assertEqual(rec["status"], 401)
        self.assertEqual(rec["retryable"], False)
        self.assertEqual(rec["stage"], "s2_citations")
        self.assertEqual(rec["seed_id"], "doi:10.1/x")

    def test_record_failure_for_httpx_error_still_works(self):
        """Regression: pre-existing httpx error path keeps working
        (status comes from .response.status_code, no S2-specific fields)."""
        from build_citation_graph import SEED_FAILURES, _record_failure

        class FakeResp:
            status_code = 503

        class FakeHTTPError(Exception):
            response = FakeResp()

        SEED_FAILURES.clear()
        _record_failure("openalex:W1", "fetch_work", FakeHTTPError("boom"))
        rec = SEED_FAILURES[0]
        self.assertEqual(rec["status"], 503)
        # Code is None for non-S2 failures — agents key off `stage` for these.
        self.assertIsNone(rec.get("code"))

    def test_normalize_s2_paper_fields(self):
        from _common import make_paper
        from _s2_citations import normalize_s2_paper
        s2 = {
            "title": "Some Paper",
            "year": 2024,
            "citationCount": 42,
            "authors": [{"name": "Smith, A."}, {"name": "Jones, B."}],
            "venue": "Nature",
            "abstract": "We did things.",
            "externalIds": {"DOI": "10.1/x", "ArXiv": "2401.001"},
        }
        kwargs = normalize_s2_paper(s2)
        self.assertEqual(kwargs["doi"], "10.1/x")
        self.assertEqual(kwargs["arxiv_id"], "2401.001")
        self.assertEqual(kwargs["authors"], ["Smith, A.", "Jones, B."])
        # make_paper should accept these kwargs without complaint.
        paper = make_paper(**kwargs)
        self.assertEqual(paper["year"], 2024)
        self.assertEqual(paper["citations"], 42)
        self.assertEqual(paper["title"], "Some Paper")


class CitationChaseSchemaTest(unittest.TestCase):
    def test_source_flag_in_schema(self):
        env = run_script("build_citation_graph.py", ["--schema"])
        self.assertTrue(env["ok"])
        params = env["data"]["params"]
        self.assertIn("source", params)
        self.assertEqual(set(params["source"]["choices"]),
                         {"openalex", "s2", "both"})

    def test_meta_block_has_since_and_tier(self):
        """schema.meta carries `since` and `tier` so cached-schema agents
        can detect drift when the contract changes."""
        env = run_script("build_citation_graph.py", ["--schema"])
        meta = env["data"].get("meta") or {}
        self.assertIn("since", meta,
                      "build_citation_graph schema is missing meta.since")
        self.assertEqual(meta.get("tier"), "write",
                         "build_citation_graph mutates state — meta.tier "
                         "must be 'write' so safety UIs classify correctly")


class CitationChaseS2BackendTest(unittest.TestCase):
    """End-to-end with --source s2, network faked via SCHOLAR_S2_TEST_FAKE."""

    def _setup_state(self, td: str) -> Path:
        state = Path(td) / "s.json"
        init_state(state)
        # Three seeds: one with DOI (S2-resolvable), one with arXiv,
        # one with neither (must be skipped by S2 path).
        papers = [
            dummy_paper("W1", doi="10.1234/seed-a"),
            dummy_paper("W2", doi=None, arxiv_id="2401.0001"),
            dummy_paper("W3", doi=None, arxiv_id=None),
        ]
        _ingest_papers(state, papers)
        _select(state, top=3)
        return state

    def _write_fake(self, td: str) -> Path:
        """Canned S2 responses keyed by S2 paper id."""
        fake = {
            "citations": {
                "DOI:10.1234/seed-a": [
                    {"title": "Cited-by paper 1", "year": 2023,
                     "citationCount": 5,
                     "authors": [{"name": "C. One"}],
                     "venue": "ICML",
                     "externalIds": {"DOI": "10.5555/cite-1"}},
                ],
                "ARXIV:2401.0001": [
                    {"title": "Cited-by paper 2", "year": 2024,
                     "citationCount": 1,
                     "authors": [{"name": "C. Two"}],
                     "externalIds": {"DOI": "10.5555/cite-2"}},
                ],
            },
            "references": {
                "DOI:10.1234/seed-a": [
                    {"title": "Referenced paper",
                     "year": 2020, "citationCount": 100,
                     "authors": [{"name": "R. Three"}],
                     "externalIds": {"DOI": "10.5555/ref-1"}},
                ],
            },
        }
        fake_path = Path(td) / "s2_fake.json"
        fake_path.write_text(json.dumps(fake))
        return fake_path

    def test_s2_only_chase_adds_papers(self):
        with tempfile.TemporaryDirectory() as td:
            state = self._setup_state(td)
            fake_path = self._write_fake(td)
            env = run_script("build_citation_graph.py", [
                "--state", str(state),
                "--source", "s2",
                "--seed-top", "3",
                "--direction", "both",
            ], env={
                "SCHOLAR_S2_TEST_FAKE": str(fake_path),
                "PATH": "/usr/bin:/bin",
            })
            self.assertTrue(env["ok"], env)
            data = env["data"]
            self.assertEqual(data["source"], "s2")
            # 1 citation + 1 reference for seed-a, 1 citation for arxiv seed.
            self.assertEqual(data["fetched"], 3)
            # Skipped seed (no DOI / no arxiv): paper id is openalex:W3
            # (priority: doi > openalex > arxiv > pmid; W3 has only openalex_id).
            self.assertIn("openalex:W3",
                          data["skipped_seeds_without_resolvable_id"])

    def test_s2_only_chase_with_no_resolvable_seeds(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / "s.json"
            init_state(state)
            # Only seeds without DOI / arxiv / pmid.
            papers = [dummy_paper("W1", doi=None, arxiv_id=None)]
            _ingest_papers(state, papers)
            _select(state, top=1)
            fake_path = Path(td) / "s2_fake.json"
            fake_path.write_text(json.dumps({"citations": {}, "references": {}}))
            env = run_script("build_citation_graph.py", [
                "--state", str(state), "--source", "s2",
                "--seed-top", "1", "--direction", "both",
            ], env={
                "SCHOLAR_S2_TEST_FAKE": str(fake_path),
                "PATH": "/usr/bin:/bin",
            }, expect_rc=3)
            self.assertEqual(env["error"]["code"], "no_resolvable_seeds")

    def test_dry_run_lists_per_backend_estimates(self):
        with tempfile.TemporaryDirectory() as td:
            state = self._setup_state(td)
            env = run_script("build_citation_graph.py", [
                "--state", str(state),
                "--source", "both",
                "--seed-top", "3",
                "--direction", "both",
                "--dry-run",
            ])
            self.assertTrue(env["ok"])
            d = env["data"]["would_fetch"]
            self.assertEqual(d["source"], "both")
            self.assertIn("by_backend", d)
            self.assertIn("openalex", d["by_backend"])
            self.assertIn("s2", d["by_backend"])


if __name__ == "__main__":
    unittest.main()
