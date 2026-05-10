"""Unit + contract coverage for `search_exa.py`.

The network layer is never touched. Normalization, DOI extraction, content
fallback, and author parsing are exercised against `SimpleNamespace` stand-ins
for `exa_py` Result objects (same attribute surface, no dependency).

Subprocess coverage verifies:
  - `--schema` works without exa-py installed (import is lazy)
  - missing `EXA_API_KEY` returns `missing_api_key` / exit 3
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))  # scripts/

from _helpers import run_script  # noqa: E402

import search_exa  # noqa: E402


def _fake_result(**kwargs):
    """Build a Result-like object with only the attributes we care about."""
    defaults = {
        "url": None, "title": None, "author": None, "authors": None,
        "published_date": None, "text": None, "highlights": None,
        "summary": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class DoiFromUrlTest(unittest.TestCase):
    def test_extracts_doi_from_doi_org(self) -> None:
        self.assertEqual(
            search_exa._doi_from_url("https://doi.org/10.1038/s41586-023-12345-6"),
            "10.1038/s41586-023-12345-6",
        )

    def test_extracts_doi_from_publisher_url(self) -> None:
        self.assertEqual(
            search_exa._doi_from_url("https://www.nature.com/articles/10.1038/nature12373"),
            "10.1038/nature12373",
        )

    def test_trims_trailing_punctuation(self) -> None:
        self.assertEqual(
            search_exa._doi_from_url("https://doi.org/10.1000/abc.def)."),
            "10.1000/abc.def",
        )

    def test_returns_none_for_non_doi(self) -> None:
        self.assertIsNone(search_exa._doi_from_url("https://example.com/paper"))
        self.assertIsNone(search_exa._doi_from_url(None))
        self.assertIsNone(search_exa._doi_from_url(""))


class YearFromPublishedTest(unittest.TestCase):
    def test_parses_iso_date(self) -> None:
        self.assertEqual(search_exa._year_from_published("2023-05-14"), 2023)

    def test_parses_bare_year(self) -> None:
        self.assertEqual(search_exa._year_from_published("2019"), 2019)

    def test_handles_missing(self) -> None:
        self.assertIsNone(search_exa._year_from_published(None))
        self.assertIsNone(search_exa._year_from_published(""))
        self.assertIsNone(search_exa._year_from_published("abc"))


class ExtractSnippetTest(unittest.TestCase):
    def test_prefers_summary_over_everything(self) -> None:
        r = _fake_result(summary="Summary wins.", text="Text body.",
                         highlights=["h1", "h2"])
        self.assertEqual(search_exa._extract_snippet(r), "Summary wins.")

    def test_falls_back_to_text_when_no_summary(self) -> None:
        r = _fake_result(text="Body text.", highlights=["h1"])
        self.assertEqual(search_exa._extract_snippet(r), "Body text.")

    def test_falls_back_to_highlights_when_no_text(self) -> None:
        r = _fake_result(highlights=["first clause", "second clause"])
        got = search_exa._extract_snippet(r)
        self.assertIsNotNone(got)
        self.assertIn("first clause", got)
        self.assertIn("second clause", got)

    def test_returns_none_when_all_empty(self) -> None:
        r = _fake_result(summary="", text=None, highlights=[])
        self.assertIsNone(search_exa._extract_snippet(r))

    def test_ignores_whitespace_only_content(self) -> None:
        r = _fake_result(summary="   ", text="\n\n", highlights=["   "])
        self.assertIsNone(search_exa._extract_snippet(r))


class AuthorsListTest(unittest.TestCase):
    def test_uses_authors_list_when_present(self) -> None:
        r = _fake_result(authors=["Jane Doe", "John Smith"])
        self.assertEqual(search_exa._authors_list(r), ["Jane Doe", "John Smith"])

    def test_splits_comma_separated_author_string(self) -> None:
        r = _fake_result(author="Jane Doe, John Smith, Ada Lovelace")
        self.assertEqual(
            search_exa._authors_list(r),
            ["Jane Doe", "John Smith", "Ada Lovelace"],
        )

    def test_splits_on_and(self) -> None:
        r = _fake_result(author="Jane Doe and John Smith")
        self.assertEqual(search_exa._authors_list(r), ["Jane Doe", "John Smith"])

    def test_single_author_stays_single(self) -> None:
        r = _fake_result(author="Jane Doe")
        self.assertEqual(search_exa._authors_list(r), ["Jane Doe"])

    def test_empty_when_nothing_present(self) -> None:
        self.assertEqual(search_exa._authors_list(_fake_result()), [])


class NormalizeTest(unittest.TestCase):
    def test_full_result_populates_paper(self) -> None:
        r = _fake_result(
            url="https://doi.org/10.1038/s41586-023-12345-6",
            title="Example Paper",
            authors=["Alice", "Bob"],
            published_date="2023-04-01",
            text="A long textual excerpt from the page.",
            highlights=["h1"],
        )
        paper = search_exa._normalize(r)
        self.assertEqual(paper["doi"], "10.1038/s41586-023-12345-6")
        self.assertEqual(paper["title"], "Example Paper")
        self.assertEqual(paper["authors"], ["Alice", "Bob"])
        self.assertEqual(paper["year"], 2023)
        self.assertEqual(paper["abstract"],
                         "A long textual excerpt from the page.")
        self.assertEqual(paper["citations"], 0)
        self.assertEqual(paper["url"], "https://doi.org/10.1038/s41586-023-12345-6")
        self.assertIsNone(paper["pdf_url"])
        self.assertIsNone(paper["venue"])

    def test_pdf_url_flagged_when_link_ends_in_pdf(self) -> None:
        r = _fake_result(
            url="https://arxiv.org/pdf/2301.00001.pdf",
            title="Preprint",
        )
        paper = search_exa._normalize(r)
        self.assertEqual(paper["pdf_url"], "https://arxiv.org/pdf/2301.00001.pdf")

    def test_no_doi_leaves_doi_none(self) -> None:
        r = _fake_result(url="https://example.com/article", title="X")
        paper = search_exa._normalize(r)
        self.assertIsNone(paper["doi"])

    def test_missing_content_produces_none_abstract(self) -> None:
        r = _fake_result(url="https://example.com/a", title="T")
        paper = search_exa._normalize(r)
        self.assertIsNone(paper["abstract"])

    def test_empty_string_title_becomes_none(self) -> None:
        # Exa returns title="" on PDF-only results where the crawler did
        # not extract a heading. Must propagate as None so downstream
        # dedupe (title-similarity) and rank do not treat "" as a valid title.
        r = _fake_result(url="https://example.com/paper.pdf", title="",
                         text="Body text.")
        paper = search_exa._normalize(r)
        self.assertIsNone(paper["title"])

    def test_whitespace_title_becomes_none(self) -> None:
        r = _fake_result(url="https://example.com/x", title="   \n  ")
        paper = search_exa._normalize(r)
        self.assertIsNone(paper["title"])

    def test_empty_string_url_becomes_none(self) -> None:
        r = _fake_result(url="", title="X")
        paper = search_exa._normalize(r)
        self.assertIsNone(paper["url"])
        self.assertIsNone(paper["pdf_url"])

    def test_camelcase_published_date_also_accepted(self) -> None:
        # exa-py has varied between snake_case and camelCase across versions.
        r = SimpleNamespace(
            url="https://example.com/x", title="T",
            author=None, authors=None, text=None,
            highlights=None, summary=None,
            publishedDate="2021-06-15",
        )
        paper = search_exa._normalize(r)
        self.assertEqual(paper["year"], 2021)


class SplitCsvTest(unittest.TestCase):
    def test_none_returns_none(self) -> None:
        self.assertIsNone(search_exa._split_csv(None))
        self.assertIsNone(search_exa._split_csv([]))

    def test_single_value_unchanged(self) -> None:
        self.assertEqual(search_exa._split_csv(["nature.com"]), ["nature.com"])

    def test_comma_separated_gets_split(self) -> None:
        self.assertEqual(
            search_exa._split_csv(["nature.com,arxiv.org", "openalex.org"]),
            ["nature.com", "arxiv.org", "openalex.org"],
        )

    def test_strips_whitespace(self) -> None:
        self.assertEqual(
            search_exa._split_csv([" nature.com , arxiv.org "]),
            ["nature.com", "arxiv.org"],
        )


class SubprocessContractTest(unittest.TestCase):
    """Black-box checks that match the envelope contract."""

    def test_schema_succeeds_without_api_key(self) -> None:
        # `--schema` must work even when exa-py is missing and no key is set.
        env = os.environ.copy()
        env.pop("EXA_API_KEY", None)
        envelope = run_script("search_exa.py", ["--schema"], env=env)
        self.assertTrue(envelope["ok"])
        self.assertEqual(envelope["data"]["command"], "search_exa")
        self.assertIn("params", envelope["data"])
        self.assertIn("query", envelope["data"]["params"])

    def test_missing_api_key_returns_validation_error(self) -> None:
        env = os.environ.copy()
        env.pop("EXA_API_KEY", None)
        env.pop("SCHOLAR_STATE_PATH", None)
        envelope = run_script(
            "search_exa.py",
            ["--query", "test"],
            expect_rc=3,
            env=env,
        )
        self.assertFalse(envelope["ok"])
        self.assertEqual(envelope["error"]["code"], "missing_api_key")


class IntegrationHeaderTest(unittest.TestCase):
    """The x-exa-integration header must be set on the client.

    Verified by capturing what `search()` does to a fake `Exa` class. The
    fake replaces `exa_py.Exa` at the source module — the lazy import in
    `search_exa.search` will therefore pick it up.
    """

    def test_header_is_set_on_client(self) -> None:
        captured: dict[str, object] = {}

        class FakeResponse:
            results: list = []

        class FakeExa:
            def __init__(self, api_key: str, user_agent: str | None = None) -> None:
                self.api_key = api_key
                self.user_agent = user_agent
                self.headers: dict[str, str] = {}
                captured["client"] = self

            def search_and_contents(self, **kwargs):
                captured["kwargs"] = kwargs
                return FakeResponse()

        fake_module = SimpleNamespace(Exa=FakeExa)
        saved = sys.modules.get("exa_py")
        sys.modules["exa_py"] = fake_module  # type: ignore[assignment]
        try:
            papers = search_exa.search(
                "q", 5, "fake-key",
                search_type="auto",
                category="research paper",
                year_from=None, year_to=None,
                include_domains=None, exclude_domains=None,
                include_text=None, exclude_text=None,
            )
        finally:
            if saved is not None:
                sys.modules["exa_py"] = saved
            else:
                sys.modules.pop("exa_py", None)

        self.assertEqual(papers, [])
        client = captured["client"]
        self.assertEqual(client.headers.get("x-exa-integration"),
                         "scholar-deep-research")
        kwargs = captured["kwargs"]
        self.assertEqual(kwargs["query"], "q")
        self.assertEqual(kwargs["num_results"], 5)
        self.assertEqual(kwargs["category"], "research paper")
        self.assertIn("text", kwargs)
        self.assertIn("highlights", kwargs)


if __name__ == "__main__":
    unittest.main()
