#!/usr/bin/env python3
"""Discover and run every test under `scripts/tests/`.

Usage:
    python scripts/tests/run.py              # verbose default
    python scripts/tests/run.py -q           # quiet

Stdlib-only. No network. Each test uses its own TemporaryDirectory, so
the suite is safe to run concurrently against a working tree.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Make `from _helpers import ...` work inside each test when this runner
# is invoked from anywhere.
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))   # so tests can import research_state


def main(argv: list[str]) -> int:
    verbosity = 2 if "-q" not in argv else 1
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=str(HERE), pattern="test_*.py",
                            top_level_dir=str(HERE))
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
