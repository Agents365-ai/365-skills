"""Concurrent ingest is serializable under the state lock.

Fires 20 parallel `ingest` subprocesses at one state file and verifies the
final paper and query counts match the inputs. Detects regressions in
`_locking.locked_rmw` or in the `apply_ingest` → lock wiring.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from _helpers import dummy_paper, init_state, make_payload, run_script


class LockingTest(unittest.TestCase):
    def test_twenty_parallel_ingests(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            state = tmp_p / "s.json"
            init_state(state)

            N = 20
            payload_paths: list[Path] = []
            for i in range(N):
                p = tmp_p / f"payload_{i}.json"
                p.write_text(json.dumps(make_payload(
                    "openalex", f"q{i}", 1, [dummy_paper(f"W{i}")],
                )))
                payload_paths.append(p)

            def run(i: int) -> int:
                env = run_script("research_state.py", [
                    "--state", str(state),
                    "ingest", "--input", str(payload_paths[i]),
                ])
                return 0 if env["ok"] else 1

            with ThreadPoolExecutor(max_workers=10) as pool:
                results = list(pool.map(run, range(N)))
            self.assertEqual(sum(results), 0, "some ingests failed")

            final = json.loads(state.read_text())
            self.assertEqual(len(final["papers"]), N)
            self.assertEqual(len(final["queries"]), N)


if __name__ == "__main__":
    unittest.main()
