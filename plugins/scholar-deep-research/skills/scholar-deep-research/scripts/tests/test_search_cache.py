"""Search-result TTL cache: opt-in via env, additive, never breaks the script.

Cache key: (source, query, limit, sorted-filters). Stored under
${SCHOLAR_CACHE_DIR}/searches/<sha256>.json with `cached_at` ISO timestamp.
Lookup is cheap; TTL is read at every call (env-overridable). Disabled by
default — existing scripts behave identically until a human/orchestrator
sets SCHOLAR_SEARCH_CACHE=1.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import with_search_cache  # noqa: E402


class SearchCacheTest(unittest.TestCase):
    """Helper-level behavior with a stub fetch."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        # Pin the cache dir so tests don't write into the repo root.
        self.env_patcher = mock.patch.dict(os.environ, {
            "SCHOLAR_CACHE_DIR": self.tmp,
        }, clear=False)
        self.env_patcher.start()
        # Default: cache is OFF. Each test that needs it on must enable
        # explicitly.
        os.environ.pop("SCHOLAR_SEARCH_CACHE", None)
        os.environ.pop("SCHOLAR_SEARCH_CACHE_TTL_HOURS", None)

    def tearDown(self) -> None:
        self.env_patcher.stop()

    def _stub(self, papers):
        calls = {"n": 0}

        def fetch():
            calls["n"] += 1
            return list(papers)

        return fetch, calls

    def test_disabled_by_default_always_fetches(self) -> None:
        """No env opt-in → cache is bypassed; every call hits fetch."""
        fetch, calls = self._stub([{"id": "p1"}])
        for _ in range(3):
            papers, meta = with_search_cache(
                source="openalex", query="q", limit=10, filters={},
                fetch=fetch,
            )
            self.assertEqual(papers, [{"id": "p1"}])
        self.assertEqual(calls["n"], 3)
        self.assertEqual(meta, {})

    def test_enabled_second_call_is_cache_hit(self) -> None:
        os.environ["SCHOLAR_SEARCH_CACHE"] = "1"
        fetch, calls = self._stub([{"id": "p1"}])
        p1, m1 = with_search_cache(
            source="openalex", query="q", limit=10, filters={"year_from": 2020},
            fetch=fetch,
        )
        p2, m2 = with_search_cache(
            source="openalex", query="q", limit=10, filters={"year_from": 2020},
            fetch=fetch,
        )
        self.assertEqual(calls["n"], 1, "fetch must be skipped on hit")
        self.assertEqual(p1, p2)
        self.assertEqual(m1["search_cache"], "miss")
        self.assertEqual(m2["search_cache"], "hit")
        self.assertIn("cached_at", m2)

    def test_different_filters_are_separate_entries(self) -> None:
        os.environ["SCHOLAR_SEARCH_CACHE"] = "1"
        fetch, calls = self._stub([{"id": "p1"}])
        with_search_cache(source="openalex", query="q", limit=10,
                          filters={"year_from": 2020}, fetch=fetch)
        with_search_cache(source="openalex", query="q", limit=10,
                          filters={"year_from": 2021}, fetch=fetch)
        self.assertEqual(calls["n"], 2, "different filter values must miss")

    def test_different_limits_are_separate_entries(self) -> None:
        os.environ["SCHOLAR_SEARCH_CACHE"] = "1"
        fetch, calls = self._stub([{"id": "p1"}])
        with_search_cache(source="openalex", query="q", limit=10, filters={},
                          fetch=fetch)
        with_search_cache(source="openalex", query="q", limit=50, filters={},
                          fetch=fetch)
        self.assertEqual(calls["n"], 2)

    def test_ttl_expiry_refetches(self) -> None:
        os.environ["SCHOLAR_SEARCH_CACHE"] = "1"
        os.environ["SCHOLAR_SEARCH_CACHE_TTL_HOURS"] = "1"
        fetch, calls = self._stub([{"id": "p1"}])
        with_search_cache(source="openalex", query="q", limit=10, filters={},
                          fetch=fetch)
        # Hand-edit the cache file to back-date it past the TTL.
        searches_dir = Path(self.tmp) / "searches"
        files = list(searches_dir.glob("*.json"))
        self.assertEqual(len(files), 1)
        entry = json.loads(files[0].read_text())
        backdate = datetime.now(timezone.utc) - timedelta(hours=2)
        entry["cached_at"] = backdate.isoformat(timespec="seconds")
        files[0].write_text(json.dumps(entry))
        # Next call must miss because the entry is older than TTL.
        _, meta = with_search_cache(source="openalex", query="q", limit=10,
                                    filters={}, fetch=fetch)
        self.assertEqual(meta["search_cache"], "miss")
        self.assertEqual(calls["n"], 2)

    def test_corrupt_cache_falls_back_to_fetch(self) -> None:
        """A malformed cache file must not break the script."""
        os.environ["SCHOLAR_SEARCH_CACHE"] = "1"
        fetch, calls = self._stub([{"id": "p1"}])
        with_search_cache(source="openalex", query="q", limit=10, filters={},
                          fetch=fetch)
        # Corrupt the only entry.
        searches_dir = Path(self.tmp) / "searches"
        for f in searches_dir.glob("*.json"):
            f.write_text("not json {")
        _, meta = with_search_cache(source="openalex", query="q", limit=10,
                                    filters={}, fetch=fetch)
        self.assertEqual(meta["search_cache"], "miss")
        self.assertEqual(calls["n"], 2)

    def test_filter_order_does_not_affect_key(self) -> None:
        """Same filters in different order must produce the same key."""
        os.environ["SCHOLAR_SEARCH_CACHE"] = "1"
        fetch, calls = self._stub([{"id": "p1"}])
        with_search_cache(source="openalex", query="q", limit=10,
                          filters={"year_from": 2020, "year_to": 2024},
                          fetch=fetch)
        with_search_cache(source="openalex", query="q", limit=10,
                          filters={"year_to": 2024, "year_from": 2020},
                          fetch=fetch)
        self.assertEqual(calls["n"], 1, "filter order must not matter")

    def test_query_whitespace_is_normalized(self) -> None:
        """Trailing/leading whitespace in query must not split the cache."""
        os.environ["SCHOLAR_SEARCH_CACHE"] = "1"
        fetch, calls = self._stub([{"id": "p1"}])
        with_search_cache(source="openalex", query="cancer therapy",
                          limit=10, filters={}, fetch=fetch)
        with_search_cache(source="openalex", query="  cancer therapy  ",
                          limit=10, filters={}, fetch=fetch)
        self.assertEqual(calls["n"], 1, "whitespace must be normalized")


if __name__ == "__main__":
    unittest.main()
