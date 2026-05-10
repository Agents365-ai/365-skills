"""Every Check.name produced by a gate must have a remediation path.

Either the name is a key in `_gates._NEXT_HINTS` (the agent gets a
suggested follow-up command on failure) or it is an explicit opt-out
(no remediation possible — typically `phase_current`, which is purely
informational, or a `host_checked` predicate that always passes).

When a future contributor adds a new gate or check, this test forces
them to either wire a hint or extend the opt-out list. It is exactly
the guardrail that would have caught the dblp/biorxiv/exa drift in
`sources_breadth`.
"""
from __future__ import annotations

import unittest

from _gates import GATES, _NEXT_HINTS

# Names that intentionally have no remediation hint:
#   phase_current             — informational; failure means the agent is on
#                               the wrong phase, no command can fix that.
#   keyword_clusters_covered  — host_checked=True, never fails mechanically.
HINT_OPT_OUT = {
    "phase_current",
    "keyword_clusters_covered",
}


def _stub_compute_saturation(_state):
    return {"per_source": {}, "overall_saturated": False}


def _all_check_names() -> set[str]:
    """Collect every Check.name any gate can emit.

    Calls each gate against a minimal empty-ish state; structure-only
    introspection — we don't care about pass/fail, only the name set.
    """
    state = {
        "schema_version": 1,
        "question": "",
        "archetype": "literature_review",
        "phase": 0,
        "queries": [],
        "papers": {},
        "selected_ids": [],
        "themes": [],
        "tensions": [],
        "self_critique": {"findings": [], "resolved": [], "appendix": ""},
    }
    names: set[str] = set()
    for target, gate in GATES.items():
        if target == 2:
            result = gate(state, compute_saturation=_stub_compute_saturation)
        else:
            result = gate(state)
        for c in result.checks:
            names.add(c.name)
    return names


class GateHintCoverageTest(unittest.TestCase):

    def test_every_check_has_hint_or_optout(self) -> None:
        names = _all_check_names()
        covered = set(_NEXT_HINTS.keys()) | HINT_OPT_OUT
        missing = names - covered
        self.assertFalse(
            missing,
            f"Check name(s) without _NEXT_HINTS entry or opt-out: {sorted(missing)}. "
            "Add a hint in _gates.py:_NEXT_HINTS, or add the name to "
            "HINT_OPT_OUT in this test if no remediation command exists.",
        )

    def test_optout_entries_are_actually_emitted(self) -> None:
        """Opt-out names should still be checks the gates emit.

        Catches dead opt-outs (e.g. a check renamed but the opt-out
        forgotten) so HINT_OPT_OUT stays minimal.
        """
        names = _all_check_names()
        stale = HINT_OPT_OUT - names
        self.assertFalse(
            stale,
            f"HINT_OPT_OUT contains name(s) no gate emits anymore: {sorted(stale)}. "
            "Remove them so the opt-out list stays accurate.",
        )

    def test_hint_keys_are_actually_emitted(self) -> None:
        """Hint keys should match real check names.

        Catches typos (a hint for `srouces_breadth` would silently never
        fire) and dead hints from removed checks.
        """
        names = _all_check_names()
        unused = set(_NEXT_HINTS.keys()) - names
        self.assertFalse(
            unused,
            f"_NEXT_HINTS has key(s) no gate emits: {sorted(unused)}. "
            "Either fix the typo or drop the entry.",
        )


if __name__ == "__main__":
    unittest.main()
