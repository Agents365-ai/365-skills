"""P2.9 — `advance` at terminal phase 7 returns ok envelope, not unknown_gate.

Plus B2 — G5 substring match accepts the dual-backend
`openalex_s2_citation_chase` source label (the default of `--source both`).

Both regressions came from the v0.13.0 test run; both fixes are
trivial in code and load-bearing for the default workflow.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from _gates import gate_5
from _helpers import init_state, run_script


def _force_phase(state_path: Path, phase: int) -> None:
    state = json.loads(state_path.read_text())
    state["phase"] = phase
    state_path.write_text(json.dumps(state))


class TerminalAdvanceTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._state = Path(self._tmp.name) / "state.json"
        init_state(self._state)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_advance_at_phase_7_returns_ok(self) -> None:
        _force_phase(self._state, 7)
        env = run_script("research_state.py", [
            "--state", str(self._state), "advance",
        ])
        self.assertTrue(env["ok"], f"expected ok envelope, got: {env}")
        self.assertEqual(env["data"]["from"], 7)
        self.assertEqual(env["data"]["to"], 7)
        self.assertTrue(env["data"]["at_terminal_phase"])
        self.assertIn("terminal", env["data"]["message"].lower())

    def test_advance_with_explicit_to_7_at_phase_7_returns_ok(self) -> None:
        _force_phase(self._state, 7)
        env = run_script("research_state.py", [
            "--state", str(self._state), "advance", "--to", "7",
        ])
        self.assertTrue(env["ok"])
        self.assertTrue(env["data"]["at_terminal_phase"])

    def test_advance_at_phase_8_still_errors_meaningfully(self) -> None:
        # If somehow phase>max, we should NOT silently say terminal —
        # that would mask state corruption. Only phase==max is "done".
        _force_phase(self._state, 8)
        env = run_script("research_state.py", [
            "--state", str(self._state), "advance",
        ], expect_rc=3)
        self.assertFalse(env["ok"])


class G5SubstringMatchTest(unittest.TestCase):
    """B2 — `_gates.gate_5` accepts every `*citation_chase*` source label."""

    @staticmethod
    def _state_with_chase_query(source_label: str, *, hits: int = 50) -> dict:
        return {
            "phase": 4,
            "queries": [{
                "source": source_label,
                "round": 1,
                "query": "chase from seed",
                "hits": hits,
                "new": hits,
            }],
            "papers": {},
            "selected_ids": [],
        }

    def test_legacy_openalex_only(self) -> None:
        state = self._state_with_chase_query("openalex_citation_chase")
        self.assertTrue(gate_5(state).met)

    def test_dual_backend_default_label(self) -> None:
        # The default of `build_citation_graph --source both`. This is
        # the label that broke G5 in 0.12.0 and forced every default
        # workflow to force-advance.
        state = self._state_with_chase_query("openalex_s2_citation_chase")
        self.assertTrue(gate_5(state).met)

    def test_s2_only_backend_label(self) -> None:
        state = self._state_with_chase_query("s2_citation_chase")
        self.assertTrue(gate_5(state).met)

    def test_unrelated_source_does_not_match(self) -> None:
        # A regular search query must NOT count as a chase query —
        # substring match could otherwise be exploited.
        state = self._state_with_chase_query("openalex")
        self.assertFalse(gate_5(state).met)

    def test_chase_with_zero_hits_blocks_productive_check(self) -> None:
        state = self._state_with_chase_query("openalex_s2_citation_chase",
                                             hits=0)
        result = gate_5(state)
        self.assertFalse(result.met)
        productive = next(c for c in result.checks
                          if c.name == "citation_chase_productive")
        self.assertFalse(productive.ok)


if __name__ == "__main__":
    unittest.main()
