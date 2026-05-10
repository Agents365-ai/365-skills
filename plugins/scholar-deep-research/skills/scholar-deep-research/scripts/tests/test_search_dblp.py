"""Unit + contract coverage for `search_dblp.py`.

DBLP returns JSON with `result.hits.hit[].info`. The `authors.author` field is
either a single dict or a list of dicts depending on count — tests pin both.

Network is never touched: normalization is exercised against the raw dict
shape DBLP returns; the subprocess test only verifies --schema works without
hitting the network.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from _helpers import run_script  # noqa: E402

import search_dblp  # noqa: E402


class NormalizeTest(unittest.TestCase):
    def test_full_hit_with_multiple_authors(self) -> None:
        info = {
            "title": "Attention Is All You Need",
            "authors": {"author": [
                {"@pid": "1", "text": "Ashish Vaswani"},
                {"@pid": "2", "text": "Noam Shazeer"},
                {"@pid": "3", "text": "Niki Parmar"},
            ]},
            "venue": "NIPS",
            "year": "2017",
            "doi": "10.5555/3295222.3295349",
            "ee": "https://arxiv.org/abs/1706.03762",
            "key": "conf/nips/VaswaniSPUJGKP17",
            "type": "Conference and Workshop Papers",
        }
        p = search_dblp._normalize(info)
        self.assertEqual(p["title"], "Attention Is All You Need")
        self.assertEqual(p["authors"], ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar"])
        self.assertEqual(p["venue"], "NIPS")
        self.assertEqual(p["year"], 2017)
        self.assertEqual(p["doi"], "10.5555/3295222.3295349")
        self.assertEqual(p["url"], "https://arxiv.org/abs/1706.03762")
        # DBLP is a bibliography catalog: no abstracts, no citations.
        self.assertIsNone(p["abstract"])
        self.assertIsNone(p["citations"])

    def test_single_author_is_dict_not_list(self) -> None:
        """DBLP returns `author: {dict}` for solo papers, not `author: [dict]`."""
        info = {
            "title": "On the Theory of Sets",
            "authors": {"author": {"@pid": "k/Knuth", "text": "Donald E. Knuth"}},
            "venue": "Bull. AMS",
            "year": "1968",
            "key": "journals/bams/Knuth68",
        }
        p = search_dblp._normalize(info)
        self.assertEqual(p["authors"], ["Donald E. Knuth"])

    def test_missing_doi_falls_through_cleanly(self) -> None:
        info = {
            "title": "An Old Paper Without DOI",
            "authors": {"author": {"@pid": "x", "text": "X. Author"}},
            "venue": "JACM",
            "year": "1962",
            "key": "journals/jacm/Author62",
        }
        p = search_dblp._normalize(info)
        self.assertIsNone(p["doi"])
        # URL falls back to a DBLP key URL when no `ee` link is present.
        self.assertEqual(p["url"], "https://dblp.org/rec/journals/jacm/Author62.html")

    def test_year_coerced_to_int(self) -> None:
        info = {"title": "X", "year": "2020", "key": "k"}
        p = search_dblp._normalize(info)
        self.assertEqual(p["year"], 2020)
        self.assertIsInstance(p["year"], int)

    def test_year_missing_is_none(self) -> None:
        info = {"title": "X", "key": "k"}
        p = search_dblp._normalize(info)
        self.assertIsNone(p["year"])

    def test_venue_array_joins_to_string(self) -> None:
        """DBLP sometimes returns `venue` as an array of strings (multi-tag entries)."""
        info = {
            "title": "X", "year": "2024",
            "venue": ["NeurIPS", "Deep Learning Track"],
            "key": "conf/x/Author24",
        }
        p = search_dblp._normalize(info)
        self.assertEqual(p["venue"], "NeurIPS, Deep Learning Track")

    def test_ee_array_picks_first(self) -> None:
        """`ee` (electronic edition link) can be a single str or list."""
        info = {
            "title": "X", "year": "2024", "key": "k",
            "ee": ["https://doi.org/10.x/y", "https://example.com/preprint.pdf"],
        }
        p = search_dblp._normalize(info)
        self.assertEqual(p["url"], "https://doi.org/10.x/y")


class SubprocessContractTest(unittest.TestCase):
    """Schema introspection works without httpx / network."""

    def test_schema_succeeds(self) -> None:
        env = run_script("search_dblp.py", ["--schema"])
        self.assertTrue(env["ok"])
        self.assertIn("query", env["data"]["params"])
        self.assertIn("limit", env["data"]["params"])


if __name__ == "__main__":
    unittest.main()
