"""export_bibtex produces non-empty output in every supported format.

Catches NameError / ImportError regressions (e.g. the `json` import that
was missing in 0.3.0) and format-sentinel regressions.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from _helpers import dummy_paper, init_state, make_payload, run_script


class ExportFormatsTest(unittest.TestCase):
    def _seed(self, state: Path, tmp: Path) -> None:
        init_state(state)
        payload = Path(tmp) / "p.json"
        payload.write_text(json.dumps(make_payload(
            "openalex", "q", 1, [dummy_paper("W1"), dummy_paper("W2")],
        )))
        run_script("research_state.py", [
            "--state", str(state), "ingest", "--input", str(payload),
        ])

    def _export(self, state: Path, tmp: Path, fmt: str) -> str:
        out = Path(tmp) / f"out.{fmt.replace('-', '.')}"
        env = run_script("export_bibtex.py", [
            "--state", str(state), "--format", fmt,
            "--output", str(out), "--all",
        ])
        self.assertTrue(env["ok"], f"export --format {fmt} failed: {env}")
        self.assertTrue(out.exists(), f"export --format {fmt} produced no file")
        return out.read_text()

    def test_bibtex(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            state = tmp_p / "s.json"
            self._seed(state, tmp_p)
            body = self._export(state, tmp_p, "bibtex")
            self.assertIn("@", body, "bibtex output missing entry sentinel")

    def test_csl_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            state = tmp_p / "s.json"
            self._seed(state, tmp_p)
            body = self._export(state, tmp_p, "csl-json")
            items = json.loads(body)
            self.assertIsInstance(items, list)
            self.assertGreaterEqual(len(items), 1)

    def test_ris(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            state = tmp_p / "s.json"
            self._seed(state, tmp_p)
            body = self._export(state, tmp_p, "ris")
            self.assertIn("TY", body, "ris output missing TY record-type tag")


if __name__ == "__main__":
    unittest.main()
