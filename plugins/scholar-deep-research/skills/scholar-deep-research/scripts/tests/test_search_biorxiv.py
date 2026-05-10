"""Unit + contract coverage for `search_biorxiv.py`.

Europe PMC indexes bioRxiv (and medRxiv — same CSHL prefix `10.1101/`)
preprints with full keyword search. We post-filter `SRC:PPR` results down
to the 10.1101 prefix so the script only returns bioRxiv/medRxiv content.

No network: tests pass canonical EPMC response dicts to the normalizer
and the prefix filter directly.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from _helpers import run_script  # noqa: E402

import search_biorxiv  # noqa: E402


class NormalizeTest(unittest.TestCase):
    def test_full_hit_lite_response(self) -> None:
        hit = {
            "id": "PPR123456",
            "source": "PPR",
            "doi": "10.1101/2024.01.15.575892",
            "title": "Spatial transcriptomics of the developing brain",
            "authorString": "Smith J, Jones K, Brown L.",
            "journalTitle": "bioRxiv",
            "pubYear": "2024",
            "firstPublicationDate": "2024-01-15",
            "citedByCount": "3",
            "fullTextUrlList": {"fullTextUrl": [
                {"availability": "Open access",
                 "url": "https://www.biorxiv.org/content/10.1101/2024.01.15.575892v1"},
                {"availability": "Open access",
                 "url": "https://www.biorxiv.org/content/10.1101/2024.01.15.575892v1.full.pdf"},
            ]},
        }
        p = search_biorxiv._normalize(hit)
        self.assertEqual(p["doi"], "10.1101/2024.01.15.575892")
        self.assertEqual(p["title"], "Spatial transcriptomics of the developing brain")
        self.assertEqual(p["authors"], ["Smith J", "Jones K", "Brown L"])
        self.assertEqual(p["venue"], "bioRxiv")
        self.assertEqual(p["year"], 2024)
        self.assertEqual(p["citations"], 3)
        self.assertTrue(p["url"].endswith("v1"))
        self.assertTrue(p["pdf_url"].endswith(".pdf"))

    def test_author_string_with_et_al_filtered(self) -> None:
        hit = {"doi": "10.1101/x", "title": "X", "pubYear": "2024",
               "authorString": "Smith J, Jones K, et al."}
        p = search_biorxiv._normalize(hit)
        self.assertEqual(p["authors"], ["Smith J", "Jones K"])

    def test_single_author_no_comma(self) -> None:
        hit = {"doi": "10.1101/x", "title": "X", "pubYear": "2020",
               "authorString": "Knuth DE."}
        p = search_biorxiv._normalize(hit)
        self.assertEqual(p["authors"], ["Knuth DE"])

    def test_year_falls_back_to_first_publication_date(self) -> None:
        hit = {"doi": "10.1101/x", "title": "X",
               "firstPublicationDate": "2023-06-12"}
        p = search_biorxiv._normalize(hit)
        self.assertEqual(p["year"], 2023)

    def test_citations_coerced_or_none(self) -> None:
        hit = {"doi": "10.1101/x", "title": "X", "citedByCount": "abc"}
        p = search_biorxiv._normalize(hit)
        self.assertIsNone(p["citations"])

    def test_pdf_url_falls_back_to_url_when_no_pdf_link(self) -> None:
        hit = {
            "doi": "10.1101/x", "title": "X",
            "fullTextUrlList": {"fullTextUrl": [
                {"availability": "Open access", "url": "https://www.biorxiv.org/abs/x"},
            ]},
        }
        p = search_biorxiv._normalize(hit)
        self.assertEqual(p["url"], "https://www.biorxiv.org/abs/x")
        self.assertIsNone(p["pdf_url"])

    def test_no_full_text_url_falls_back_to_doi_org(self) -> None:
        hit = {"doi": "10.1101/x", "title": "X"}
        p = search_biorxiv._normalize(hit)
        self.assertEqual(p["url"], "https://doi.org/10.1101/x")


class PrefixFilterTest(unittest.TestCase):
    def test_keeps_biorxiv_and_medrxiv_prefix(self) -> None:
        hits = [
            {"doi": "10.1101/2024.01.15.575892", "title": "bioRxiv paper"},
            {"doi": "10.1101/2024.05.20.123456", "title": "medRxiv paper"},
            {"doi": "10.21203/rs.3.rs-1234567/v1", "title": "ResearchSquare paper"},
            {"doi": "10.31234/osf.io/abcde", "title": "PsyArXiv paper"},
            {"doi": None, "title": "Preprint without DOI"},
        ]
        kept = search_biorxiv._filter_to_biorxiv(hits)
        self.assertEqual(len(kept), 2)
        self.assertTrue(all(h["doi"].startswith("10.1101/") for h in kept))


class SubprocessContractTest(unittest.TestCase):
    def test_schema_succeeds(self) -> None:
        env = run_script("search_biorxiv.py", ["--schema"])
        self.assertTrue(env["ok"])
        self.assertIn("query", env["data"]["params"])


if __name__ == "__main__":
    unittest.main()
