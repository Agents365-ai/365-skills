"""Smoke tests for SOURCE_META on every search_*.py and list_sources.py.

Pins three contracts:
  1. Every search_*.py exposes a SOURCE_META dict.
  2. Every SOURCE_META passes validate_source_meta (vocab, types, fields).
  3. list_sources.py aggregates all of them and respects its filters.
"""
from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from _helpers import run_script  # noqa: E402
from _search_meta import validate_source_meta  # noqa: E402


SEARCH_SCRIPTS = sorted(p.stem for p in ROOT.glob("search_*.py"))


class SourceMetaPerScriptTest(unittest.TestCase):
    """Iterate every search_*.py and require a valid SOURCE_META."""

    def test_every_search_script_exposes_source_meta(self):
        # If a new search_*.py lands without SOURCE_META, this test
        # catches it on the next CI run — the registry stays complete.
        for mod_name in SEARCH_SCRIPTS:
            with self.subTest(module=mod_name):
                mod = importlib.import_module(mod_name)
                meta = getattr(mod, "SOURCE_META", None)
                self.assertIsNotNone(
                    meta, f"{mod_name} missing SOURCE_META")
                self.assertIsInstance(meta, dict)
                errors = validate_source_meta(meta)
                self.assertEqual(
                    errors, [],
                    f"{mod_name}.SOURCE_META validation failed: {errors}")

    def test_source_meta_name_matches_filename(self):
        """SOURCE_META['name'] must equal the search_<name>.py stem."""
        for mod_name in SEARCH_SCRIPTS:
            with self.subTest(module=mod_name):
                expected = mod_name.removeprefix("search_")
                mod = importlib.import_module(mod_name)
                self.assertEqual(mod.SOURCE_META["name"], expected)


class ValidatorEdgeCasesTest(unittest.TestCase):
    def test_missing_field(self):
        errors = validate_source_meta({"name": "x"})
        self.assertTrue(any("missing field: domain" in e for e in errors))

    def test_bad_domain_value(self):
        errors = validate_source_meta({
            "name": "x", "domain": "bogus", "index_type": "web_search",
            "covers": [], "lookup_by": [], "freshness_lag_days": 0,
            "rate_limit_qps_polite": 1.0, "auth": "none",
            "needs_relevance_filter": False, "language_scope": [],
        })
        self.assertTrue(any("domain must be one of" in e for e in errors))

    def test_list_field_must_be_list(self):
        errors = validate_source_meta({
            "name": "x", "domain": "general", "index_type": "web_search",
            "covers": "papers",  # should be a list
            "lookup_by": [], "freshness_lag_days": 0,
            "rate_limit_qps_polite": 1.0, "auth": "none",
            "needs_relevance_filter": False, "language_scope": [],
        })
        self.assertTrue(any("covers must be a list" in e for e in errors))


class ListSourcesCliTest(unittest.TestCase):
    def test_schema_exposes_filter_flags(self):
        env = run_script("list_sources.py", ["--schema"])
        params = env["data"]["params"]
        for flag in ("domain", "index_type", "auth",
                     "needs_relevance_filter"):
            self.assertIn(flag, params)

    def test_full_list_returns_seven_sources(self):
        env = run_script("list_sources.py", [])
        self.assertTrue(env["ok"], env)
        self.assertEqual(env["data"]["total_available"], len(SEARCH_SCRIPTS))
        self.assertEqual(env["data"]["count"], len(SEARCH_SCRIPTS))
        self.assertEqual(env["data"]["validation_warnings"], [])

    def test_domain_filter(self):
        env = run_script("list_sources.py", ["--domain", "academic"])
        names = sorted(s["name"] for s in env["data"]["sources"])
        # academic = openalex + crossref currently; add new ones here when
        # they land. A new academic source landing without this test
        # update is a deliberate signal to revisit the categorization.
        self.assertEqual(names, ["crossref", "openalex"])

    def test_auth_none_filter(self):
        env = run_script("list_sources.py", ["--auth", "none"])
        names = sorted(s["name"] for s in env["data"]["sources"])
        self.assertEqual(names, ["arxiv", "biorxiv", "dblp"])

    def test_needs_relevance_filter_true_picks_exa(self):
        env = run_script("list_sources.py",
                         ["--needs-relevance-filter", "true"])
        names = [s["name"] for s in env["data"]["sources"]]
        self.assertEqual(names, ["exa"])


if __name__ == "__main__":
    unittest.main()
