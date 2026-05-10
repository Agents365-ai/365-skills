"""Every public script emits a valid `--schema` envelope.

Catches regressions where a new script forgets `maybe_emit_schema`, or
where a module-level import (like `httpx`, `pypdf`) breaks schema
discovery on a clean machine.
"""
from __future__ import annotations

import unittest

from _helpers import all_script_names, run_script


class SchemaContractTest(unittest.TestCase):
    def test_every_script_has_schema(self) -> None:
        for name in all_script_names():
            with self.subTest(script=name):
                env = run_script(name, ["--schema"], expect_rc=0)
                self.assertTrue(env.get("ok"),
                                f"{name} --schema did not emit ok envelope: {env}")
                data = env.get("data") or {}
                self.assertIn("command", data, f"{name}: data.command missing")
                self.assertIn("params", data, f"{name}: data.params missing")
                self.assertIn("exit_codes", data, f"{name}: data.exit_codes missing")


if __name__ == "__main__":
    unittest.main()
