"""Smoke tests for extract_pdf.py engine selector + idempotency.

No network. Uses a synthetic blank PDF written by pypdf so the pypdf
branch can run end-to-end. The docling branch only verifies the
`missing_dependency` envelope when docling is not installed (the import
guard in extract_pdf.py is what's being pinned).
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from _helpers import run_script  # noqa: E402


def _make_blank_pdf(path: Path) -> None:
    """Write a 1-page blank PDF that pypdf can read."""
    from pypdf import PdfWriter
    w = PdfWriter()
    w.add_blank_page(width=72, height=72)
    with open(path, "wb") as f:
        w.write(f)


class EngineSchemaTest(unittest.TestCase):
    def test_schema_exposes_engine_choices(self):
        env = run_script("extract_pdf.py", ["--schema"])
        params = env["data"]["params"]
        self.assertIn("engine", params)
        self.assertEqual(set(params["engine"]["choices"]),
                         {"auto", "pypdf", "docling"})
        self.assertEqual(params["engine"]["default"], "auto")
        self.assertIn("idempotency_key", params)


class PypdfEngineTest(unittest.TestCase):
    def test_pypdf_engine_returns_text_format(self):
        with tempfile.TemporaryDirectory() as td:
            pdf = Path(td) / "blank.pdf"
            _make_blank_pdf(pdf)
            env = run_script("extract_pdf.py", [
                "--input", str(pdf),
                "--engine", "pypdf",
            ])
            self.assertTrue(env["ok"], env)
            data = env["data"]
            self.assertEqual(data["engine"], "pypdf")
            self.assertEqual(data["format"], "text")
            # blank page → 0 chars → looks_scanned True. The auto fallback
            # would try docling here; the explicit pypdf engine should NOT.
            self.assertTrue(data["looks_scanned"])
            self.assertNotIn("engine_fallback_reason", data)

    def test_auto_no_docling_returns_pypdf_with_fallback_note(self):
        """When pypdf produces empty output AND docling isn't installed,
        auto mode must still return the pypdf result and explain why it
        didn't upgrade — never silently swallow the signal."""
        try:
            import docling  # noqa: F401
            self.skipTest("docling is installed; this test pins the absent path")
        except ImportError:
            pass
        with tempfile.TemporaryDirectory() as td:
            pdf = Path(td) / "blank.pdf"
            _make_blank_pdf(pdf)
            env = run_script("extract_pdf.py", [
                "--input", str(pdf),
                "--engine", "auto",
            ])
            self.assertTrue(env["ok"], env)
            self.assertEqual(env["data"]["engine"], "pypdf")
            self.assertIn("engine_fallback_reason", env["data"])
            self.assertIn("docling not installed",
                          env["data"]["engine_fallback_reason"])


class DoclingMissingTest(unittest.TestCase):
    def test_force_docling_when_absent_errors_missing_dependency(self):
        try:
            import docling  # noqa: F401
            self.skipTest("docling is installed; this test pins the absent path")
        except ImportError:
            pass
        with tempfile.TemporaryDirectory() as td:
            pdf = Path(td) / "blank.pdf"
            _make_blank_pdf(pdf)
            env = run_script("extract_pdf.py", [
                "--input", str(pdf),
                "--engine", "docling",
            ], expect_rc=1)
            self.assertFalse(env["ok"])
            self.assertEqual(env["error"]["code"], "missing_dependency")
            self.assertEqual(env["error"]["dependency"], "docling")


class IdempotencyReplayTest(unittest.TestCase):
    def test_retry_replays_text_and_rewrites_output(self):
        with tempfile.TemporaryDirectory() as td:
            os.environ["SCHOLAR_CACHE_DIR"] = str(Path(td) / "cache")
            try:
                pdf = Path(td) / "blank.pdf"
                _make_blank_pdf(pdf)
                out = Path(td) / "out.txt"

                env1 = run_script("extract_pdf.py", [
                    "--input", str(pdf),
                    "--engine", "pypdf",
                    "--output", str(out),
                    "--idempotency-key", "k1",
                ], env={**os.environ})
                self.assertTrue(env1["ok"], env1)
                self.assertFalse(env1["meta"].get("cache_hit", False))
                self.assertTrue(out.exists())

                # Delete the output file — the retry must rewrite it from
                # the cache, not just return the meta envelope.
                out.unlink()
                self.assertFalse(out.exists())

                env2 = run_script("extract_pdf.py", [
                    "--input", str(pdf),
                    "--engine", "pypdf",
                    "--output", str(out),
                    "--idempotency-key", "k1",
                ], env={**os.environ})
                self.assertTrue(env2["ok"], env2)
                self.assertTrue(env2["meta"]["cache_hit"])
                self.assertTrue(out.exists(),
                                "cache hit must rewrite the --output file")
            finally:
                os.environ.pop("SCHOLAR_CACHE_DIR", None)

    def test_same_key_different_args_returns_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            os.environ["SCHOLAR_CACHE_DIR"] = str(Path(td) / "cache")
            try:
                pdf = Path(td) / "blank.pdf"
                _make_blank_pdf(pdf)

                env1 = run_script("extract_pdf.py", [
                    "--input", str(pdf),
                    "--engine", "pypdf",
                    "--idempotency-key", "k2",
                ], env={**os.environ})
                self.assertTrue(env1["ok"], env1)

                # Same key, different --engine value → must mismatch.
                env2 = run_script("extract_pdf.py", [
                    "--input", str(pdf),
                    "--engine", "auto",
                    "--idempotency-key", "k2",
                ], env={**os.environ}, expect_rc=3)
                self.assertFalse(env2["ok"])
                self.assertEqual(env2["error"]["code"],
                                 "idempotency_key_mismatch")
            finally:
                os.environ.pop("SCHOLAR_CACHE_DIR", None)


if __name__ == "__main__":
    unittest.main()
