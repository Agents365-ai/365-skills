"""Unit coverage for `check_update.commits_summary`.

Tests the pure-Python part: parsing git output and the degrade-silent
guarantee. The git invocation itself is monkey-patched, so the test
doesn't need a fake git repo.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import check_update  # noqa: E402


class CommitsSummaryTest(unittest.TestCase):
    def setUp(self) -> None:
        self._orig_run_git = check_update.run_git

    def tearDown(self) -> None:
        check_update.run_git = self._orig_run_git

    def _stub_git(self, rc: int, stdout: str, stderr: str = "") -> None:
        check_update.run_git = lambda *args: (rc, stdout, stderr)

    def test_returns_subjects_capped_at_limit(self) -> None:
        self._stub_git(0, "\n".join([
            "feat(phase1): add DBLP source",
            "fix(phase1): venue axis edge case",
            "feat(phase3): prefetch PDFs",
            "feat(phase1): TTL cache",
            "feat(phase1): saturation axes",
            "fix(phase2): rank weight bug",  # 6th — must be dropped
        ]))
        out = check_update.commits_summary("a", "b", limit=5)
        self.assertEqual(len(out), 5)
        self.assertEqual(out[0], "feat(phase1): add DBLP source")
        self.assertNotIn("fix(phase2): rank weight bug", out)

    def test_empty_output_returns_empty_list(self) -> None:
        self._stub_git(0, "")
        self.assertEqual(check_update.commits_summary("a", "b"), [])

    def test_git_failure_returns_empty_list(self) -> None:
        """Degrade-silent: a broken git log must never raise."""
        self._stub_git(128, "", "fatal: bad revision")
        self.assertEqual(check_update.commits_summary("a", "b"), [])


if __name__ == "__main__":
    unittest.main()
