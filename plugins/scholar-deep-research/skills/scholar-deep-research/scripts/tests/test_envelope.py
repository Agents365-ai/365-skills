"""`research_state.py` emits a single envelope per invocation.

Every call must print exactly one JSON object to stdout. No prose,
no double-envelopes. Success/failure cases both checked.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from _helpers import init_state, run_script


class EnvelopeContractTest(unittest.TestCase):
    def test_init_and_query_are_single_envelope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "state.json"
            init_state(state)
            env = run_script("research_state.py",
                             ["--state", str(state), "query", "summary"],
                             expect_rc=0)
            self.assertTrue(env["ok"])
            self.assertIn("papers", env["data"])

    def test_state_not_found_errs_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ghost = Path(tmp) / "ghost.json"
            env = run_script("research_state.py",
                             ["--state", str(ghost), "query", "summary"],
                             expect_rc=4)
            self.assertFalse(env["ok"])
            self.assertEqual(env["error"]["code"], "state_not_found")

    def test_set_rejects_forbidden_field(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "state.json"
            init_state(state)
            # `phase` must not be settable after C9 — the only way is advance.
            env = run_script("research_state.py", [
                "--state", str(state), "set", "--field", "phase", "--value", "3"
            ], expect_rc=3)
            self.assertFalse(env["ok"])
            self.assertEqual(env["error"]["code"], "field_not_settable")
            self.assertNotIn("phase", env["error"]["allowed"])


if __name__ == "__main__":
    unittest.main()
