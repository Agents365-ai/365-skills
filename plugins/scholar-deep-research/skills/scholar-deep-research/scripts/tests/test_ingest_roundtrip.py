"""Ingest is idempotent and validates payload shape.

Re-ingesting the same payload twice must not duplicate papers. Bad
payloads must fail with `invalid_payload` / exit 3.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from _helpers import dummy_paper, init_state, make_payload, run_script


class IngestRoundtripTest(unittest.TestCase):
    def test_reingest_does_not_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            init_state(state)
            payload_path = Path(tmp) / "payload.json"
            payload_path.write_text(json.dumps(make_payload(
                "openalex", "q", 1,
                [dummy_paper("W1"), dummy_paper("W2")],
            )))
            first = run_script("research_state.py", [
                "--state", str(state), "ingest", "--input", str(payload_path),
            ])
            self.assertTrue(first["ok"])
            self.assertEqual(first["data"]["new"], 2)
            second = run_script("research_state.py", [
                "--state", str(state), "ingest", "--input", str(payload_path),
            ])
            self.assertTrue(second["ok"])
            self.assertEqual(second["data"]["new"], 0)
            self.assertEqual(second["data"]["merged"], 2)
            self.assertEqual(second["data"]["total_papers"], 2)

    def test_invalid_payload_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            init_state(state)
            bad_path = Path(tmp) / "bad.json"
            # missing `round` and `papers`
            bad_path.write_text(json.dumps({"source": "x", "query": "q"}))
            env = run_script("research_state.py", [
                "--state", str(state), "ingest", "--input", str(bad_path),
            ], expect_rc=3)
            self.assertEqual(env["error"]["code"], "invalid_payload")
            self.assertSetEqual(set(env["error"]["missing"]), {"round", "papers"})


if __name__ == "__main__":
    unittest.main()
