"""evidence --from-json: agents skip the multi-quote shell escape dance.

Phase 3 sub-agents compose evidence in Python; piping a JSON object via
--from-json is far less fragile than `--method '...' --findings 'a' 'b'
--limitations '...'` with embedded quotes and unicode. The structured
mode stays as the original path; mixing both is rejected.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _helpers import init_state, run_script, ROOT


def _state_with_paper(state_path: Path) -> str:
    """Init state and inject one paper. Returns its id."""
    init_state(state_path)
    s = json.loads(state_path.read_text())
    s["papers"]["doi:10.1234/x"] = {
        "id": "doi:10.1234/x",
        "title": "Sample paper",
        "authors": ["A. Author"],
        "year": 2024,
        "doi": "10.1234/x",
        "tier": "deep",
        "depth": "shallow",
    }
    s["selected_ids"] = ["doi:10.1234/x"]
    state_path.write_text(json.dumps(s, indent=2))
    return "doi:10.1234/x"


class FromJsonFileTest(unittest.TestCase):

    def test_writes_evidence_from_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            pid = _state_with_paper(state)
            payload = Path(tmp) / "ev.json"
            payload.write_text(json.dumps({
                "method": "Pretrained 800M-param transformer on 100M cells",
                "findings": [
                    "92.91% accuracy on 8 intra-datasets",
                    "Outperforms scFoundation by +2.02% on cell-type annotation",
                ],
                "limitations": "Human-only; no spatial coverage",
                "relevance": "Demonstrates 100M-cell scale is reachable",
                "depth": "full",
            }))
            env = run_script("research_state.py", [
                "--state", str(state), "evidence",
                "--id", pid,
                "--from-json", str(payload),
            ])
            self.assertEqual(env["data"]["depth"], "full")
            written = json.loads(state.read_text())["papers"][pid]["evidence"]
            self.assertIn("800M-param", written["method"])
            self.assertEqual(len(written["findings"]), 2)
            self.assertEqual(written["limitations"], "Human-only; no spatial coverage")

    def test_depth_in_json_overrides_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            pid = _state_with_paper(state)
            payload = Path(tmp) / "ev.json"
            payload.write_text(json.dumps({
                "method": "evidence_unavailable: pdf_fetch_failed",
                "findings": ["From abstract: ..."],
                "limitations": "Marked evidence_unavailable",
                "relevance": "Pending source recovery",
                "depth": "shallow",
            }))
            env = run_script("research_state.py", [
                "--state", str(state), "evidence",
                "--id", pid,
                "--from-json", str(payload),
            ])
            # JSON's "shallow" wins over argparse's default "full".
            self.assertEqual(env["data"]["depth"], "shallow")

    def test_depth_falls_back_to_flag_when_absent_in_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            pid = _state_with_paper(state)
            payload = Path(tmp) / "ev.json"
            payload.write_text(json.dumps({
                "method": "Pretrained transformer",
                "findings": ["..."],
            }))
            # --depth specified on CLI; JSON omits it
            env = run_script("research_state.py", [
                "--state", str(state), "evidence",
                "--id", pid,
                "--from-json", str(payload),
                "--depth", "shallow",
            ])
            self.assertEqual(env["data"]["depth"], "shallow")


class FromJsonStdinTest(unittest.TestCase):

    def test_dash_reads_stdin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            pid = _state_with_paper(state)
            payload = json.dumps({
                "method": "Test method via stdin",
                "findings": ["finding-1", "finding-2"],
                "limitations": "lim",
                "relevance": "rel",
            })
            cmd = [sys.executable,
                   str(ROOT / "scripts" / "research_state.py"),
                   "--state", str(state), "evidence",
                   "--id", pid, "--from-json", "-"]
            proc = subprocess.run(cmd, input=payload, capture_output=True,
                                  text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            env = json.loads(proc.stdout)
            self.assertEqual(env["data"]["id"], pid)
            written = json.loads(state.read_text())["papers"][pid]["evidence"]
            self.assertEqual(written["method"], "Test method via stdin")


class RejectsMixedModesTest(unittest.TestCase):

    def test_from_json_with_method_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            pid = _state_with_paper(state)
            payload = Path(tmp) / "ev.json"
            payload.write_text('{"method":"x","findings":["y"]}')
            env = run_script("research_state.py", [
                "--state", str(state), "evidence",
                "--id", pid,
                "--from-json", str(payload),
                "--method", "should not be allowed",
            ], expect_rc=3)
            self.assertEqual(env["error"]["code"], "inconsistent_input")


class RejectsBadJsonTest(unittest.TestCase):

    def test_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            pid = _state_with_paper(state)
            bad = Path(tmp) / "bad.json"
            bad.write_text("{not json")
            env = run_script("research_state.py", [
                "--state", str(state), "evidence",
                "--id", pid, "--from-json", str(bad),
            ], expect_rc=3)
            self.assertEqual(env["error"]["code"], "invalid_json")

    def test_payload_not_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            pid = _state_with_paper(state)
            arr = Path(tmp) / "arr.json"
            arr.write_text('["just","an","array"]')
            env = run_script("research_state.py", [
                "--state", str(state), "evidence",
                "--id", pid, "--from-json", str(arr),
            ], expect_rc=3)
            self.assertEqual(env["error"]["code"], "invalid_json")

    def test_missing_method(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            pid = _state_with_paper(state)
            empty = Path(tmp) / "empty.json"
            empty.write_text('{"findings": ["x"]}')
            env = run_script("research_state.py", [
                "--state", str(state), "evidence",
                "--id", pid, "--from-json", str(empty),
            ], expect_rc=3)
            self.assertEqual(env["error"]["code"], "missing_field")
            self.assertEqual(env["error"]["field"], "method")

    def test_findings_must_be_list_of_strings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            pid = _state_with_paper(state)
            bad = Path(tmp) / "bad.json"
            bad.write_text('{"method":"x","findings":[1,2,3]}')
            env = run_script("research_state.py", [
                "--state", str(state), "evidence",
                "--id", pid, "--from-json", str(bad),
            ], expect_rc=3)
            self.assertEqual(env["error"]["code"], "invalid_field")
            self.assertEqual(env["error"]["field"], "findings")

    def test_invalid_depth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            pid = _state_with_paper(state)
            bad = Path(tmp) / "bad.json"
            bad.write_text('{"method":"x","findings":["y"],"depth":"deep"}')
            env = run_script("research_state.py", [
                "--state", str(state), "evidence",
                "--id", pid, "--from-json", str(bad),
            ], expect_rc=3)
            self.assertEqual(env["error"]["code"], "invalid_field")
            self.assertEqual(env["error"]["field"], "depth")

    def test_unreadable_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            pid = _state_with_paper(state)
            env = run_script("research_state.py", [
                "--state", str(state), "evidence",
                "--id", pid,
                "--from-json", str(Path(tmp) / "does-not-exist.json"),
            ], expect_rc=3)
            self.assertEqual(env["error"]["code"], "from_json_unreadable")


class StructuredModeStillWorksTest(unittest.TestCase):
    """Original path stays intact — the JSON addition is purely additive."""

    def test_structured_method_required(self) -> None:
        # Before, --method was argparse-required (rc=2 from argparse).
        # Now it's runtime-required, returning a structured envelope.
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            pid = _state_with_paper(state)
            env = run_script("research_state.py", [
                "--state", str(state), "evidence",
                "--id", pid,
            ], expect_rc=3)
            self.assertEqual(env["error"]["code"], "missing_field")

    def test_structured_path_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            pid = _state_with_paper(state)
            env = run_script("research_state.py", [
                "--state", str(state), "evidence",
                "--id", pid,
                "--method", "structured method",
                "--findings", "a", "b",
                "--limitations", "lim",
                "--relevance", "rel",
                "--depth", "full",
            ])
            self.assertEqual(env["data"]["depth"], "full")
            ev = json.loads(state.read_text())["papers"][pid]["evidence"]
            self.assertEqual(ev["method"], "structured method")
            self.assertEqual(ev["findings"], ["a", "b"])


if __name__ == "__main__":
    unittest.main()
