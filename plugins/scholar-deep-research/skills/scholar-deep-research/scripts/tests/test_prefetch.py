"""End-to-end (no-network) tests for prefetch_pdfs + apply_pdf_paths.

Uses subprocess (the same harness as the rest of the smoke suite) so the
test exercises the actual envelope contract — argparse, with_idempotency,
ok/err — not just the internal Python API. fetch_pdf is monkey-patched
via SCHOLAR_PREFETCH_TEST_FAKE: when that env var points at a JSON file,
prefetch_pdfs uses the recorded fake outcomes instead of touching paper-
fetch / Unpaywall. The fake hook is gated to the test path only.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _helpers import dummy_paper, init_state, run_script

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"


def _ingest_papers(state: Path, papers: list[dict]) -> None:
    payload = {"source": "openalex", "query": "test", "round": 1,
               "papers": papers}
    payload_path = state.parent / "payload.json"
    payload_path.write_text(json.dumps(payload))
    env = run_script("research_state.py", [
        "--state", str(state), "ingest", "--input", str(payload_path),
    ])
    assert env.get("ok"), f"ingest failed: {env}"


def _select_and_triage(state: Path) -> None:
    """Run rank + select + skim_papers so prefetch has a deep tier."""
    env = run_script("rank_papers.py", ["--state", str(state), "--top", "10"])
    assert env.get("ok")
    env = run_script("research_state.py", [
        "--state", str(state), "select", "--top", "10",
    ])
    assert env.get("ok")
    env = run_script("skim_papers.py", [
        "--state", str(state),
        "--deep-ratio", "0.5", "--skim-ratio", "0.5",
    ])
    assert env.get("ok")


class PrefetchSchemaTest(unittest.TestCase):
    """prefetch_pdfs --schema must produce a valid envelope."""

    def test_schema(self):
        env = run_script("prefetch_pdfs.py", ["--schema"], expect_rc=0)
        self.assertTrue(env.get("ok"), f"prefetch_pdfs --schema: {env}")
        self.assertEqual(env["data"]["command"], "prefetch_pdfs")
        params = env["data"]["params"]
        for required in ("tier", "concurrency", "out_dir", "dry_run",
                         "idempotency_key"):
            self.assertIn(required, params,
                          f"prefetch_pdfs schema missing param '{required}'")
        # Tier flag must be enum-constrained for safety.
        self.assertIn("choices", params["tier"])
        self.assertEqual(set(params["tier"]["choices"]),
                         {"deep", "skim", "defer"})


class PrefetchDryRunTest(unittest.TestCase):
    """Dry-run must not mutate state and must report what would happen."""

    def test_dry_run_lists_candidates(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / "s.json"
            init_state(state)
            papers = [dummy_paper(f"W{i}", doi=f"10.1234/test{i}",
                                  pdf_url=f"https://x/pdf/{i}.pdf")
                      for i in range(8)]
            _ingest_papers(state, papers)
            _select_and_triage(state)

            env = run_script("prefetch_pdfs.py", [
                "--state", str(state), "--tier", "deep", "--dry-run",
            ])
            self.assertTrue(env.get("ok"))
            self.assertTrue(env["data"]["dry_run"])
            # 8 papers, top 50% deep = 4 candidates.
            self.assertEqual(env["data"]["would_fetch"], 4)
            self.assertEqual(len(env["data"]["would_fetch_ids"]), 4)


class ApplyPdfPathsTest(unittest.TestCase):
    """The apply_pdf_paths replay subcommand survives a roundtrip."""

    def test_replay_via_prefetch_subcommand(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / "s.json"
            init_state(state)
            # Use DOIs that match the normalize_doi regex (10\.\d{4,9}/...).
            papers = [dummy_paper("W1", doi="10.1234/aaa"),
                      dummy_paper("W2", doi="10.1234/bbb")]
            _ingest_papers(state, papers)

            patch = {
                "pdf_records": {
                    "doi:10.1234/aaa": {
                        "id": "doi:10.1234/aaa",
                        "pdf_status": "ok",
                        "pdf_path": "/tmp/a.pdf",
                        "pdf_source": "unpaywall",
                        "pdf_bytes": 1024,
                    },
                    "doi:10.1234/bbb": {
                        "id": "doi:10.1234/bbb",
                        "pdf_status": "failed",
                        "pdf_failure_code": "no_open_access_pdf",
                        "pdf_failure_reason": "paywall",
                        "pdf_failure_retryable": False,
                    },
                },
            }
            patch_path = Path(td) / "prefetch.patch.json"
            patch_path.write_text(json.dumps(patch))

            env = run_script("research_state.py", [
                "--state", str(state), "prefetch",
                "--patch", str(patch_path),
            ])
            self.assertTrue(env.get("ok"), f"prefetch replay: {env}")
            self.assertEqual(env["data"]["applied"], 2)
            self.assertEqual(env["data"]["unknown"], 0)
            by_status = env["data"]["by_status"]
            self.assertEqual(by_status.get("ok"), 1)
            self.assertEqual(by_status.get("failed"), 1)

            saved = json.loads(state.read_text())
            ok_paper = saved["papers"]["doi:10.1234/aaa"]
            self.assertEqual(ok_paper["pdf_status"], "ok")
            self.assertEqual(ok_paper["pdf_path"], "/tmp/a.pdf")
            self.assertEqual(ok_paper["pdf_bytes"], 1024)
            failed_paper = saved["papers"]["doi:10.1234/bbb"]
            self.assertEqual(failed_paper["pdf_status"], "failed")
            self.assertEqual(failed_paper["pdf_failure_code"],
                             "no_open_access_pdf")

    def test_unknown_id_counted_not_errored(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / "s.json"
            init_state(state)
            patch = {"pdf_records": {
                "doi:not.in.state": {"id": "doi:not.in.state",
                                     "pdf_status": "ok",
                                     "pdf_path": "/tmp/x.pdf"},
            }}
            patch_path = Path(td) / "p.json"
            patch_path.write_text(json.dumps(patch))

            env = run_script("research_state.py", [
                "--state", str(state), "prefetch",
                "--patch", str(patch_path),
            ])
            self.assertTrue(env.get("ok"))
            self.assertEqual(env["data"]["applied"], 0)
            self.assertEqual(env["data"]["unknown"], 1)


class EmitManifestTest(unittest.TestCase):
    """--emit-manifest surfaces a hand-fetch list, read-only."""

    def _setup_with_failures(self, td: str) -> tuple[Path, list[str]]:
        """Initialise state with 4 deep-tier papers, two marked as failed
        and one with no DOI. Returns (state_path, deep_ids)."""
        state = Path(td) / "s.json"
        init_state(state)
        papers = [
            dummy_paper("W1", doi="10.1234/aaa"),
            dummy_paper("W2", doi="10.1234/bbb"),
            dummy_paper("W3", doi=None),
            dummy_paper("W4", doi="10.1234/ddd"),
        ]
        _ingest_papers(state, papers)
        _select_and_triage(state)

        # Mark W1 + W2 as failed via the prefetch replay subcommand so the
        # manifest sees realistic failure state.
        patch = {"pdf_records": {
            "doi:10.1234/aaa": {"id": "doi:10.1234/aaa",
                                "pdf_status": "failed",
                                "pdf_failure_code": "no_open_access_pdf",
                                "pdf_failure_reason": "paywall",
                                "pdf_failure_retryable": False},
            "doi:10.1234/bbb": {"id": "doi:10.1234/bbb",
                                "pdf_status": "failed",
                                "pdf_failure_code": "paper_fetch_error",
                                "pdf_failure_reason": "all sources exhausted",
                                "pdf_failure_retryable": False},
        }}
        patch_path = Path(td) / "patch.json"
        patch_path.write_text(json.dumps(patch))
        env = run_script("research_state.py", [
            "--state", str(state), "prefetch", "--patch", str(patch_path),
        ])
        assert env["ok"], env

        s = json.loads(state.read_text())
        deep_ids = [pid for pid in s["selected_ids"]
                    if s["papers"][pid].get("tier") == "deep"]
        return state, deep_ids

    def test_lists_failed_and_no_doi(self):
        with tempfile.TemporaryDirectory() as td:
            state, deep_ids = self._setup_with_failures(td)
            out_dir = Path(td) / "pdfs"
            env = run_script("prefetch_pdfs.py", [
                "--state", str(state),
                "--tier", "deep",
                "--out-dir", str(out_dir),
                "--emit-manifest",
            ])
            self.assertTrue(env["ok"])
            entries = env["data"]["needs_user_download"]
            ids = {e["id"] for e in entries}
            # Every deep-tier paper without a cached PDF should appear.
            self.assertEqual(ids, set(deep_ids))
            # Each entry carries an absolute drop path under --out-dir.
            for e in entries:
                self.assertTrue(e["drop_at"].startswith(str(out_dir)))
                self.assertTrue(e["drop_at"].endswith(".pdf"))
            # current_status reflects state for failed papers.
            statuses = {e["id"]: e["current_status"] for e in entries}
            failed = [pid for pid, s in statuses.items() if s == "failed"]
            self.assertGreaterEqual(len(failed), 1)

    def test_is_read_only(self):
        with tempfile.TemporaryDirectory() as td:
            state, _ = self._setup_with_failures(td)
            before = state.read_bytes()
            run_script("prefetch_pdfs.py", [
                "--state", str(state), "--tier", "deep",
                "--out-dir", str(Path(td) / "pdfs"),
                "--emit-manifest",
            ])
            after = state.read_bytes()
            self.assertEqual(before, after,
                             "--emit-manifest must not mutate state")

    def test_skips_cached_papers(self):
        with tempfile.TemporaryDirectory() as td:
            state, deep_ids = self._setup_with_failures(td)
            out_dir = Path(td) / "pdfs"
            # Mark one paper as already cached (real file on disk).
            cached_id = deep_ids[0]
            patch = {"pdf_records": {cached_id: {
                "id": cached_id,
                "pdf_status": "ok",
                "pdf_path": str(Path(td) / "cached.pdf"),
                "pdf_source": "unpaywall",
                "pdf_bytes": 100,
            }}}
            (Path(td) / "cached.pdf").write_bytes(b"%PDF-stub")
            patch_path = Path(td) / "p.json"
            patch_path.write_text(json.dumps(patch))
            run_script("research_state.py", [
                "--state", str(state), "prefetch", "--patch", str(patch_path),
            ])

            env = run_script("prefetch_pdfs.py", [
                "--state", str(state), "--tier", "deep",
                "--out-dir", str(out_dir), "--emit-manifest",
            ])
            ids = {e["id"] for e in env["data"]["needs_user_download"]}
            self.assertNotIn(cached_id, ids)

    def test_rejects_combination_with_dry_run(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / "s.json"
            init_state(state)
            env = run_script("prefetch_pdfs.py", [
                "--state", str(state), "--emit-manifest", "--dry-run",
            ], expect_rc=3)
            self.assertEqual(env["error"]["code"], "inconsistent_input")


class AbsorbDroppedPdfTest(unittest.TestCase):
    """When the user drops a PDF at the manifest's drop_at path, the
    next prefetch run picks it up as cached without re-attempting fetch."""

    def test_dropped_pdf_classified_as_cached(self):
        # Run a normal --dry-run first to confirm the candidate would
        # have been fetched, then drop a file and assert the next
        # --dry-run sees it as cached (no fetch needed).
        import hashlib

        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / "s.json"
            init_state(state)
            papers = [dummy_paper(f"W{i}", doi=f"10.1234/test{i}")
                      for i in range(8)]
            _ingest_papers(state, papers)
            _select_and_triage(state)

            out_dir = Path(td) / "pdfs"
            env = run_script("prefetch_pdfs.py", [
                "--state", str(state), "--tier", "deep",
                "--out-dir", str(out_dir), "--dry-run",
            ])
            would_fetch = set(env["data"]["would_fetch_ids"])
            self.assertGreater(len(would_fetch), 0)

            # User drops a file at the predicted subdir for one of them.
            target_id = sorted(would_fetch)[0]
            subdir = out_dir / hashlib.sha256(
                target_id.encode("utf-8")).hexdigest()[:24]
            subdir.mkdir(parents=True)
            (subdir / "manual.pdf").write_bytes(b"%PDF-1.4 fake content")

            env = run_script("prefetch_pdfs.py", [
                "--state", str(state), "--tier", "deep",
                "--out-dir", str(out_dir), "--dry-run",
            ])
            after = set(env["data"]["would_fetch_ids"])
            self.assertNotIn(target_id, after,
                             "user-dropped PDF must remove paper from to-fetch list")
            # Skipped count went up by 1 with status 'cached'.
            self.assertEqual(env["data"]["skipped"]["by_status"].get("cached", 0), 1)


if __name__ == "__main__":
    unittest.main()
