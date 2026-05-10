"""Unit tests for the _pdf_fetch shared helper.

No network: subprocess to paper-fetch is mocked, and the Unpaywall path
is not exercised here (its httpx call is mocked indirectly via the
fallback gate, which we bypass).

Two contracts to pin:
  1. find_paper_fetch_script honors PAPER_FETCH_SCRIPT env override.
  2. fetch_pdf raises typed FetchError with code/message/retryable on
     each documented failure path, so callers (extract_pdf and
     prefetch_pdfs) can translate uniformly.
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

# Make scripts/ importable for direct test access.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from _pdf_fetch import (  # noqa: E402
    FetchError, fetch_pdf, find_paper_fetch_script,
)


class _FakeCompleted:
    """Drop-in for subprocess.CompletedProcess."""
    def __init__(self, returncode: int, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class FindPaperFetchScriptTest(unittest.TestCase):
    def test_env_override_when_file_exists(self):
        """PAPER_FETCH_SCRIPT pointing at a real file wins."""
        with mock.patch.dict(os.environ, {"PAPER_FETCH_SCRIPT": __file__}):
            self.assertEqual(find_paper_fetch_script(), Path(__file__))

    def test_env_override_missing_falls_through(self):
        """A bad env override does not blow up — we fall to convention paths."""
        with mock.patch.dict(os.environ,
                             {"PAPER_FETCH_SCRIPT": "/nope/missing.py"}):
            # Convention paths are unlikely on a CI box; result may be
            # None or an actual installed path. Both are fine — the
            # contract is "no exception."
            try:
                find_paper_fetch_script()
            except Exception as e:  # pragma: no cover - defensive
                self.fail(f"find_paper_fetch_script raised: {e}")


class FetchPdfPaperFetchPathTest(unittest.TestCase):
    """fetch_pdf when paper-fetch is available."""

    def setUp(self):
        # Use a real script path so the function thinks paper-fetch
        # exists; we mock subprocess.run so it never actually runs.
        self.fetch_script = Path(__file__)

    def _run_fetch(self, return_value, tmp_path, *, fallback=True):
        with mock.patch("_pdf_fetch.subprocess.run",
                        return_value=return_value):
            return fetch_pdf(
                "10.1234/x",
                out_dir=tmp_path,
                fetch_script=self.fetch_script,
                fallback_unpaywall=fallback,
            )

    def test_success_returns_pdf_and_meta(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            pdf = tmp / "paper.pdf"
            pdf.write_bytes(b"%PDF-1.4 stub")
            envelope = {
                "ok": True,
                "data": {
                    "local_path": str(pdf),
                    "source": "unpaywall",
                    "title": "Test",
                    "year": 2024,
                    "pdf_url": "https://example.com/x.pdf",
                },
            }
            stub = _FakeCompleted(0, json.dumps(envelope))
            with mock.patch("_pdf_fetch.subprocess.run", return_value=stub):
                got_path, meta = fetch_pdf(
                    "10.1234/x", out_dir=tmp,
                    fetch_script=self.fetch_script,
                )
            self.assertEqual(got_path, pdf)
            self.assertEqual(meta["source"], "unpaywall")
            self.assertEqual(meta["title"], "Test")

    def test_subprocess_failure_raises_paper_fetch_failed(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            stub = _FakeCompleted(2, "{}", "boom")
            with self.assertRaises(FetchError) as cm:
                self._run_fetch(stub, Path(td), fallback=False)
            self.assertEqual(cm.exception.code, "paper_fetch_failed")
            self.assertTrue(cm.exception.retryable,
                            "rc=2 is upstream-retryable per paper-fetch contract")

    def test_non_json_stdout_raises_bad_response(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            stub = _FakeCompleted(0, "not json at all")
            with self.assertRaises(FetchError) as cm:
                self._run_fetch(stub, Path(td), fallback=False)
            self.assertEqual(cm.exception.code, "paper_fetch_bad_response")

    def test_envelope_error_raises_paper_fetch_error(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            envelope = {"ok": False, "error": {
                "code": "paywall", "message": "no OA",
                "retryable": False,
            }}
            stub = _FakeCompleted(0, json.dumps(envelope))
            with self.assertRaises(FetchError) as cm:
                self._run_fetch(stub, Path(td), fallback=False)
            self.assertEqual(cm.exception.code, "paper_fetch_error")
            self.assertEqual(cm.exception.ctx.get("upstream_code"), "paywall")

    def test_fallback_only_on_no_pdf_or_bad_response(self):
        """A `paper_fetch_error` (paywall) must NOT silently retry via Unpaywall."""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            envelope = {"ok": False, "error": {
                "code": "paywall", "message": "no OA", "retryable": False,
            }}
            stub = _FakeCompleted(0, json.dumps(envelope))
            with self.assertRaises(FetchError) as cm:
                # fallback=True, but the error code is `paper_fetch_error`,
                # not `paper_fetch_no_pdf` / `paper_fetch_bad_response`,
                # so Unpaywall must NOT be retried.
                self._run_fetch(stub, Path(td), fallback=True)
            self.assertEqual(cm.exception.code, "paper_fetch_error",
                             "must propagate without dropping to Unpaywall")


class FetchErrorEnvelopeTest(unittest.TestCase):
    def test_carries_envelope_ready_attrs(self):
        e = FetchError("x_code", "x message", retryable=True, doi="10.1/y", k=42)
        self.assertEqual(e.code, "x_code")
        self.assertEqual(e.message, "x message")
        self.assertTrue(e.retryable)
        self.assertEqual(e.ctx, {"doi": "10.1/y", "k": 42})


if __name__ == "__main__":
    unittest.main()
