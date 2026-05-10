"""enforce_min_interval throttles same-source calls without crossing sources.

Covers the three observable behaviours each search script depends on:
  1. First call for a source returns immediately (no sleep).
  2. A second call within the window sleeps the remaining gap.
  3. Different sources don't block each other (separate lock files).
  4. Cross-process coordination — a worker thread that opens its own
     limiter handle still observes the timestamp from a prior call.
"""
from __future__ import annotations

import os
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from _common import enforce_min_interval


class EnforceMinIntervalTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._prev_cache = os.environ.get("SCHOLAR_CACHE_DIR")
        os.environ["SCHOLAR_CACHE_DIR"] = self._tmp.name

    def tearDown(self) -> None:
        if self._prev_cache is None:
            os.environ.pop("SCHOLAR_CACHE_DIR", None)
        else:
            os.environ["SCHOLAR_CACHE_DIR"] = self._prev_cache
        self._tmp.cleanup()

    def test_first_call_no_sleep(self) -> None:
        # No prior timestamp file → returns immediately, sleep duration = 0.
        slept = enforce_min_interval("test_source_first", 1.0)
        self.assertEqual(slept, 0.0)

    def test_zero_or_negative_interval_is_noop(self) -> None:
        slept = enforce_min_interval("test_source_zero", 0.0)
        self.assertEqual(slept, 0.0)
        slept = enforce_min_interval("test_source_zero", -1.0)
        self.assertEqual(slept, 0.0)

    def test_second_call_sleeps_remaining_window(self) -> None:
        enforce_min_interval("test_source_pair", 0.5)
        t0 = time.time()
        slept = enforce_min_interval("test_source_pair", 0.5)
        elapsed = time.time() - t0
        self.assertGreater(slept, 0.0,
                           "second call within window should report a sleep")
        # Allow generous slack for scheduler jitter, but require we waited.
        self.assertGreaterEqual(elapsed, 0.4)
        self.assertLess(elapsed, 1.5)

    def test_different_sources_do_not_block(self) -> None:
        enforce_min_interval("test_source_a", 5.0)
        t0 = time.time()
        slept = enforce_min_interval("test_source_b", 5.0)
        elapsed = time.time() - t0
        self.assertEqual(slept, 0.0)
        self.assertLess(elapsed, 0.5,
                        "different source should not have queued behind first")

    def test_third_call_after_window_no_sleep(self) -> None:
        enforce_min_interval("test_source_window", 0.2)
        time.sleep(0.3)
        slept = enforce_min_interval("test_source_window", 0.2)
        self.assertEqual(slept, 0.0,
                         "outside the window the call should not throttle")

    def test_concurrent_callers_serialise(self) -> None:
        """N parallel calls to the same source should queue, not stampede."""
        N = 4
        gap = 0.3

        def call(_: int) -> tuple[float, float]:
            t0 = time.time()
            slept = enforce_min_interval("test_source_concurrent", gap)
            return slept, time.time() - t0

        with ThreadPoolExecutor(max_workers=N) as pool:
            t_start = time.time()
            results = list(pool.map(call, range(N)))
            t_total = time.time() - t_start

        # The wall-clock for N serialised calls with `gap` between each
        # is at least (N-1) * gap. Allow generous slack for scheduler.
        self.assertGreaterEqual(
            t_total, (N - 1) * gap * 0.8,
            f"expected ≥{(N - 1) * gap:.2f}s for {N} serialised calls, "
            f"got {t_total:.2f}s; sleeps={[r[0] for r in results]}",
        )

    def test_lock_file_under_cache_dir(self) -> None:
        enforce_min_interval("test_source_path", 0.1)
        expected = Path(self._tmp.name) / "rate" / "test_source_path.lock"
        self.assertTrue(expected.is_file(), f"missing lock file: {expected}")

    def test_unsanitised_source_name_normalised(self) -> None:
        # Slashes / spaces in a source label should not escape the rate
        # directory or create unintended subdirectories.
        enforce_min_interval("Test/Source With Space", 0.1)
        rate_dir = Path(self._tmp.name) / "rate"
        files = list(rate_dir.iterdir())
        self.assertEqual(len(files), 1, f"unexpected layout: {files}")
        self.assertNotIn("/", files[0].name)
        self.assertNotIn(" ", files[0].name)


if __name__ == "__main__":
    unittest.main()
