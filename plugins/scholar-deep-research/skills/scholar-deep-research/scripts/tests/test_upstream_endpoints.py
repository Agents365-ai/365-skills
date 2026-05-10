"""Regression tests for upstream-API contract drift.

These pin two specific defects discovered during v0.6.0 e2e testing:

1. arXiv now hard-redirects http -> https; if the script's API constant
   keeps `http://`, every search returns `upstream_error` with status 301.
2. OpenAlex deprecated and removed the `host_venue` field; including it in
   the `select=` query param returns 400. The citation-graph script must
   request only `primary_location` instead.

Both checks are pure source-text assertions — no network needed.
"""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"


class ArxivEndpointTest(unittest.TestCase):
    def test_api_constant_uses_https(self):
        src = (SCRIPTS / "search_arxiv.py").read_text()
        self.assertIn(
            'API = "https://export.arxiv.org/api/query"', src,
            "search_arxiv.py must use https://; arXiv 301-redirects "
            "http requests and httpx does not auto-follow.",
        )
        self.assertNotIn(
            'API = "http://export.arxiv.org', src,
            "search_arxiv.py still references the http:// arXiv endpoint.",
        )


class OpenAlexSelectFieldsTest(unittest.TestCase):
    def test_citation_graph_does_not_request_host_venue(self):
        src = (SCRIPTS / "build_citation_graph.py").read_text()
        self.assertNotIn(
            "host_venue", src,
            "build_citation_graph.py must not include the deprecated "
            "`host_venue` field in OpenAlex select=; the API now returns 400. "
            "Use `primary_location` only.",
        )

    def test_citation_graph_still_requests_primary_location(self):
        src = (SCRIPTS / "build_citation_graph.py").read_text()
        self.assertIn(
            "primary_location", src,
            "build_citation_graph.py must keep `primary_location` in select=; "
            "the normalizer reads venue from it.",
        )


if __name__ == "__main__":
    unittest.main()
