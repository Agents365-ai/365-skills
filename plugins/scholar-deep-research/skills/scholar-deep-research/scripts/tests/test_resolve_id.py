"""Unit + contract coverage for `resolve_id.py`.

The resolver is a pure function — no network, no state, no cache. Tests
exercise each ID kind plus the unknown path and the schema introspection.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from _helpers import run_script  # noqa: E402

import resolve_id  # noqa: E402


class DOIDetectionTest(unittest.TestCase):
    def test_bare_doi(self) -> None:
        r = resolve_id.resolve_id("10.1145/3534678.3539115")
        self.assertEqual(r["canonical_id"], "doi:10.1145/3534678.3539115")
        self.assertEqual(r["detected_kind"], "doi")
        self.assertIn("openalex", r["available_sources"])
        self.assertIn("crossref", r["available_sources"])

    def test_doi_url(self) -> None:
        r = resolve_id.resolve_id("https://doi.org/10.1038/nature12373")
        self.assertEqual(r["canonical_id"], "doi:10.1038/nature12373")
        self.assertIn("extracted DOI from doi.org URL",
                      r["normalization_notes"])

    def test_doi_prefixed(self) -> None:
        r = resolve_id.resolve_id("doi:10.1038/nature12373")
        self.assertEqual(r["canonical_id"], "doi:10.1038/nature12373")
        self.assertIn("stripped doi: prefix", r["normalization_notes"])

    def test_doi_uppercase_lowercased(self) -> None:
        r = resolve_id.resolve_id("10.1145/ABCDE.12345")
        self.assertEqual(r["canonical_id"], "doi:10.1145/abcde.12345")
        self.assertIn("lowercased DOI", r["normalization_notes"])

    def test_biorxiv_doi_adds_biorxiv_source(self) -> None:
        r = resolve_id.resolve_id("10.1101/2024.01.15.575892")
        self.assertEqual(r["detected_kind"], "doi")
        self.assertIn("biorxiv", r["available_sources"])

    def test_arxiv_doi_adds_arxiv_source(self) -> None:
        r = resolve_id.resolve_id("10.48550/arxiv.2301.12345")
        self.assertEqual(r["detected_kind"], "doi")
        self.assertIn("arxiv", r["available_sources"])


class OpenAlexDetectionTest(unittest.TestCase):
    def test_uppercase_w_id(self) -> None:
        r = resolve_id.resolve_id("W2059403765")
        self.assertEqual(r["canonical_id"], "openalex:W2059403765")
        self.assertEqual(r["detected_kind"], "openalex")
        self.assertEqual(r["available_sources"], ["openalex"])

    def test_lowercase_w_uppercased(self) -> None:
        r = resolve_id.resolve_id("w2059403765")
        self.assertEqual(r["canonical_id"], "openalex:W2059403765")
        self.assertIn("uppercased W prefix", r["normalization_notes"])


class ArxivDetectionTest(unittest.TestCase):
    def test_new_style(self) -> None:
        r = resolve_id.resolve_id("2301.12345")
        self.assertEqual(r["canonical_id"], "arxiv:2301.12345")

    def test_new_style_with_version(self) -> None:
        r = resolve_id.resolve_id("2301.12345v2")
        self.assertEqual(r["canonical_id"], "arxiv:2301.12345v2")

    def test_old_style(self) -> None:
        r = resolve_id.resolve_id("hep-th/9901001")
        self.assertEqual(r["canonical_id"], "arxiv:hep-th/9901001")

    def test_arxiv_prefixed(self) -> None:
        r = resolve_id.resolve_id("arxiv:2301.12345")
        self.assertEqual(r["canonical_id"], "arxiv:2301.12345")
        self.assertIn("stripped arxiv: prefix", r["normalization_notes"])

    def test_arxiv_url(self) -> None:
        r = resolve_id.resolve_id("https://arxiv.org/abs/2301.12345")
        self.assertEqual(r["canonical_id"], "arxiv:2301.12345")
        self.assertIn("extracted arXiv ID from URL",
                      r["normalization_notes"])

    def test_arxiv_pdf_url_strips_pdf_and_version(self) -> None:
        r = resolve_id.resolve_id("https://arxiv.org/pdf/2301.12345v3.pdf")
        self.assertEqual(r["canonical_id"], "arxiv:2301.12345")


class PmidDetectionTest(unittest.TestCase):
    def test_bare_digits(self) -> None:
        r = resolve_id.resolve_id("12345678")
        self.assertEqual(r["canonical_id"], "pmid:12345678")
        self.assertEqual(r["detected_kind"], "pmid")
        self.assertEqual(r["available_sources"], ["pubmed"])

    def test_pmid_prefixed(self) -> None:
        r = resolve_id.resolve_id("pmid:12345678")
        self.assertEqual(r["canonical_id"], "pmid:12345678")
        self.assertIn("stripped pmid: prefix", r["normalization_notes"])


class UnknownDetectionTest(unittest.TestCase):
    def test_garbage_returns_unknown(self) -> None:
        r = resolve_id.resolve_id("not-an-id-at-all")
        self.assertIsNone(r["canonical_id"])
        self.assertEqual(r["detected_kind"], "unknown")
        self.assertEqual(r["available_sources"], [])

    def test_empty_returns_unknown(self) -> None:
        r = resolve_id.resolve_id("")
        self.assertIsNone(r["canonical_id"])
        self.assertEqual(r["detected_kind"], "unknown")

    def test_whitespace_stripped(self) -> None:
        r = resolve_id.resolve_id("  10.1145/abc.123  ")
        self.assertEqual(r["canonical_id"], "doi:10.1145/abc.123")
        self.assertIn("stripped surrounding whitespace",
                      r["normalization_notes"])


class SubprocessContractTest(unittest.TestCase):
    def test_schema_succeeds(self) -> None:
        env = run_script("resolve_id.py", ["--schema"])
        self.assertTrue(env["ok"])
        self.assertIn("id", env["data"]["params"])
        self.assertEqual(env["data"]["params"]["id"]["positional"], True)

    def test_resolve_via_cli(self) -> None:
        env = run_script("resolve_id.py", ["10.1038/nature12373"])
        self.assertTrue(env["ok"])
        self.assertEqual(env["data"]["canonical_id"],
                         "doi:10.1038/nature12373")
        self.assertEqual(env["data"]["detected_kind"], "doi")


if __name__ == "__main__":
    unittest.main()
