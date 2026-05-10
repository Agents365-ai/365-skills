"""B3 — `normalize_title(None)` and `make_paper_id({title: None})` are safe.

Exa's `_str_or_none` deliberately produces `title=None` for crawler
results without an extractable heading. In 0.12.0 that crashed
`normalize_title` (`'NoneType' object has no attribute 'lower'`) and
killed the entire ingest batch. The 0.13.0 fix is a 3-line guard;
this test pins it.
"""
from __future__ import annotations

import unittest

from research_state import make_paper_id, normalize_title


class NormalizeTitleNoneTest(unittest.TestCase):
    def test_none_returns_empty_string(self) -> None:
        self.assertEqual(normalize_title(None), "")

    def test_empty_string_returns_empty(self) -> None:
        self.assertEqual(normalize_title(""), "")

    def test_normal_title_still_works(self) -> None:
        self.assertEqual(normalize_title("Hello, World!"), "hello world")


class MakePaperIdNullTitleTest(unittest.TestCase):
    def test_null_title_no_doi_returns_title_prefix(self) -> None:
        # Should not crash, even though the result is uninteresting.
        pid = make_paper_id({"title": None})
        self.assertTrue(pid.startswith("title:"))

    def test_null_title_with_doi_uses_doi(self) -> None:
        pid = make_paper_id({"doi": "10.1234/abc", "title": None})
        self.assertEqual(pid, "doi:10.1234/abc")

    def test_null_title_with_arxiv_id_uses_arxiv(self) -> None:
        pid = make_paper_id({"title": None, "arxiv_id": "2306.05685"})
        self.assertEqual(pid, "arxiv:2306.05685")

    def test_default_title_get_does_not_help_against_explicit_none(self) -> None:
        # Sanity: `dict.get("title", "")` returns None when the key is
        # explicitly set to None — that's why the code now uses
        # `paper.get("title") or ""`. This test guards against someone
        # "simplifying" make_paper_id back to the broken pattern.
        paper = {"title": None}
        # If the code regressed to `paper.get("title", "")`, this would
        # crash with AttributeError instead of returning a title:... id.
        result = make_paper_id(paper)
        self.assertIsInstance(result, str)


if __name__ == "__main__":
    unittest.main()
