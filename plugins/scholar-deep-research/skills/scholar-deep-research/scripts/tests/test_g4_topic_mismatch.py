"""F5 — G4 accepts depth=shallow + method^='topic_mismatch:' as valid coverage.

Companion escape hatch to `evidence_unavailable:`. Both let a deep-tier
paper finish with depth=shallow without blocking phase 3→4 advancement
when the agent has a recorded reason.

Cases:
  - depth=full → counts (baseline)
  - depth=shallow + evidence_unavailable: → counts (legacy escape)
  - depth=shallow + topic_mismatch: → counts (new in 0.13.0)
  - depth=shallow with no magic prefix → does NOT count (regression guard)
"""
from __future__ import annotations

import unittest

from _gates import gate_4


def _state_with_deep_tier(deep_papers: list[dict]) -> dict:
    """deep_papers: list of {depth, evidence_method?} for each paper."""
    papers = {}
    selected_ids = []
    for i, p in enumerate(deep_papers):
        pid = f"doi:test/{i}"
        rec = {
            "id": pid, "title": f"Paper {i}",
            "tier": "deep", "selected": True,
            "depth": p["depth"],
        }
        if "evidence_method" in p:
            rec["evidence"] = {"method": p["evidence_method"]}
        papers[pid] = rec
        selected_ids.append(pid)
    return {
        "phase": 3,
        "papers": papers,
        "selected_ids": selected_ids,
    }


class G4TopicMismatchTest(unittest.TestCase):
    def test_all_full_passes(self) -> None:
        state = _state_with_deep_tier([
            {"depth": "full"}, {"depth": "full"}, {"depth": "full"},
        ])
        result = gate_4(state)
        self.assertTrue(result.met)

    def test_topic_mismatch_counts_as_coverage(self) -> None:
        state = _state_with_deep_tier([
            {"depth": "full"},
            {"depth": "shallow",
             "evidence_method": "topic_mismatch: paper is about Med-PaLM"},
        ])
        result = gate_4(state)
        self.assertTrue(result.met,
                        f"topic_mismatch should count: {result.checks}")
        # Detail string should mention both buckets.
        deep_check = next(c for c in result.checks
                          if c.name == "deep_tier_full_evidence")
        self.assertIn("topic_mismatch", deep_check.detail)

    def test_evidence_unavailable_still_counts(self) -> None:
        # Regression guard for the legacy escape hatch.
        state = _state_with_deep_tier([
            {"depth": "full"},
            {"depth": "shallow",
             "evidence_method": "evidence_unavailable: paywall_no_oa"},
        ])
        self.assertTrue(gate_4(state).met)

    def test_both_escapes_in_one_run(self) -> None:
        state = _state_with_deep_tier([
            {"depth": "full"},
            {"depth": "shallow",
             "evidence_method": "evidence_unavailable: scanned_no_ocr"},
            {"depth": "shallow",
             "evidence_method": "topic_mismatch: off-topic survey"},
        ])
        result = gate_4(state)
        self.assertTrue(result.met)
        deep_check = next(c for c in result.checks
                          if c.name == "deep_tier_full_evidence")
        self.assertIn("evidence_unavailable", deep_check.detail)
        self.assertIn("topic_mismatch", deep_check.detail)

    def test_bare_shallow_without_prefix_blocks(self) -> None:
        # Regression guard: a shallow record without the magic prefix
        # must not silently pass the gate (otherwise an agent that
        # writes generic shallow evidence would skip the deep-read
        # contract entirely).
        state = _state_with_deep_tier([
            {"depth": "full"},
            {"depth": "shallow",
             "evidence_method": "I just decided not to fetch"},
        ])
        self.assertFalse(gate_4(state).met)

    def test_shallow_with_no_evidence_at_all_blocks(self) -> None:
        # No evidence object = agent crashed before write → must block.
        state = _state_with_deep_tier([
            {"depth": "full"},
            {"depth": "shallow"},  # no evidence_method
        ])
        self.assertFalse(gate_4(state).met)

    def test_topic_mismatch_must_have_prefix_at_start(self) -> None:
        # Substring-anywhere matching would be a security/clarity hole;
        # the prefix must be at the start of the method string.
        state = _state_with_deep_tier([
            {"depth": "full"},
            {"depth": "shallow",
             "evidence_method": "we noticed topic_mismatch: late in our read"},
        ])
        self.assertFalse(gate_4(state).met)


if __name__ == "__main__":
    unittest.main()
