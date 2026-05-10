"""Tests for the agent-native-cli upgrade surface.

Covers:
 - Auto-populated envelope meta (request_id, latency_ms, cli_version, schema_version)
 - export_bibtex envelope fallback when stdout is not a TTY
 - init --force / --dangerous gating (confirmation_required)
 - Idempotency keys: hit, miss, signature mismatch, dry-run conflict
 - Dry-run on rank_papers and the replay subcommands
 - `next` hints on gate failure envelopes
 - Schema metadata: cli_version top-level, per-subcommand `meta.since` / `tier`
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from _helpers import dummy_paper, init_state, make_payload, run_script


class AutoMetaTest(unittest.TestCase):
    def test_ok_envelope_has_auto_meta(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            init_state(state)
            env = run_script("research_state.py",
                             ["--state", str(state), "query", "summary"])
            self.assertIn("meta", env)
            self.assertIn("request_id", env["meta"])
            self.assertIn("latency_ms", env["meta"])
            self.assertIn("cli_version", env["meta"])
            self.assertIn("schema_version", env["meta"])

    def test_err_envelope_has_auto_meta(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ghost = Path(tmp) / "ghost.json"
            env = run_script("research_state.py",
                             ["--state", str(ghost), "query", "summary"],
                             expect_rc=4)
            self.assertIn("meta", env)
            self.assertEqual(env["meta"]["cli_version"].count("."), 2,
                             "cli_version should be semver x.y.z")


class ExportBibtexEnvelopeTest(unittest.TestCase):
    def test_piped_stdout_emits_envelope_with_body_inline(self) -> None:
        # run_script redirects through subprocess → stdout is not a TTY →
        # export_bibtex should emit an envelope, not raw bibtex.
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            state = tmp_p / "s.json"
            init_state(state)
            payload = tmp_p / "p.json"
            payload.write_text(json.dumps(make_payload(
                "openalex", "q", 1, [dummy_paper("W1")]
            )))
            run_script("research_state.py", [
                "--state", str(state), "ingest", "--input", str(payload),
            ])
            env = run_script("export_bibtex.py", [
                "--state", str(state), "--format", "bibtex", "--all",
            ])
            self.assertTrue(env["ok"])
            self.assertIn("body", env["data"])
            self.assertTrue(env["data"]["body"].startswith("@"))


class InitDangerousTest(unittest.TestCase):
    def test_force_without_dangerous_emits_confirmation_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            init_state(state)
            env = run_script("research_state.py", [
                "--state", str(state), "init",
                "--question", "t2", "--archetype", "literature_review",
                "--force",
            ], expect_rc=3)
            self.assertEqual(env["error"]["code"], "confirmation_required")
            self.assertIn("existing", env["error"])

    def test_force_with_dangerous_proceeds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            init_state(state)
            env = run_script("research_state.py", [
                "--state", str(state), "init",
                "--question", "t2", "--archetype", "literature_review",
                "--force", "--dangerous",
            ])
            self.assertTrue(env["ok"])


class IdempotencyTest(unittest.TestCase):
    def _seed(self, state: Path, payload: Path) -> None:
        init_state(state)
        payload.write_text(json.dumps(make_payload(
            "openalex", "q", 1, [dummy_paper("W1"), dummy_paper("W2")],
        )))

    def test_cache_miss_then_hit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            state = tmp_p / "s.json"
            payload = tmp_p / "p.json"
            self._seed(state, payload)
            env_ns = dict(os.environ)
            env_ns["SCHOLAR_CACHE_DIR"] = str(tmp_p / "cache")
            first = run_script("research_state.py", [
                "--state", str(state), "ingest",
                "--input", str(payload), "--idempotency-key", "k-a",
            ], env=env_ns)
            self.assertTrue(first["ok"])
            self.assertFalse(first["meta"]["cache_hit"])
            second = run_script("research_state.py", [
                "--state", str(state), "ingest",
                "--input", str(payload), "--idempotency-key", "k-a",
            ], env=env_ns)
            self.assertTrue(second["meta"]["cache_hit"])

    def test_signature_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            state = tmp_p / "s.json"
            payload_a = tmp_p / "a.json"
            payload_b = tmp_p / "b.json"
            self._seed(state, payload_a)
            payload_b.write_text(payload_a.read_text())
            env_ns = dict(os.environ)
            env_ns["SCHOLAR_CACHE_DIR"] = str(tmp_p / "cache")
            run_script("research_state.py", [
                "--state", str(state), "ingest",
                "--input", str(payload_a), "--idempotency-key", "k-b",
            ], env=env_ns)
            env = run_script("research_state.py", [
                "--state", str(state), "ingest",
                "--input", str(payload_b), "--idempotency-key", "k-b",
            ], env=env_ns, expect_rc=3)
            self.assertEqual(env["error"]["code"], "idempotency_key_mismatch")

    def test_dry_run_with_idempotency_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            state = tmp_p / "s.json"
            patch = tmp_p / "patch.json"
            init_state(state)
            patch.write_text(json.dumps({"scored_papers": {}, "meta": {}}))
            env = run_script("research_state.py", [
                "--state", str(state), "rank",
                "--patch", str(patch), "--dry-run", "--idempotency-key", "k-c",
            ], expect_rc=3)
            self.assertEqual(env["error"]["code"], "idempotency_with_dry_run")


class DryRunTest(unittest.TestCase):
    def test_rank_replay_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            state = tmp_p / "s.json"
            init_state(state)
            patch = tmp_p / "p.json"
            patch.write_text(json.dumps({
                "scored_papers": {"openalex:W1": {"score": 0.5, "score_components": {}}},
                "meta": {"formula": "x"},
            }))
            env = run_script("research_state.py", [
                "--state", str(state), "rank", "--patch", str(patch), "--dry-run",
            ])
            self.assertTrue(env["ok"])
            self.assertTrue(env["data"].get("dry_run"))
            # state should not have been mutated by the dry-run:
            saved = json.loads(state.read_text())
            self.assertNotIn("ranking", saved)

    def test_rank_papers_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            state = tmp_p / "s.json"
            init_state(state)
            payload = tmp_p / "pay.json"
            payload.write_text(json.dumps(make_payload(
                "openalex", "q", 1, [dummy_paper("W1")]
            )))
            run_script("research_state.py", [
                "--state", str(state), "ingest", "--input", str(payload),
            ])
            env = run_script("rank_papers.py", [
                "--state", str(state), "--dry-run",
            ])
            self.assertTrue(env["data"].get("dry_run"))
            saved = json.loads(state.read_text())
            # rank_papers dry-run must not write state.ranking:
            self.assertNotIn("ranking", saved)


class GateNextHintsTest(unittest.TestCase):
    def test_g2_failure_carries_next_hints(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            # Build a phase=1 state with no queries yet
            state.write_text(json.dumps({
                "schema_version": 1, "question": "t",
                "archetype": "literature_review", "phase": 1,
                "queries": [], "papers": {}, "selected_ids": [],
                "themes": [], "tensions": [],
                "self_critique": {"findings": [], "resolved": [], "appendix": ""},
                "report_path": None,
            }))
            env = run_script("research_state.py", [
                "--state", str(state), "advance", "--to", "2",
            ], expect_rc=3)
            self.assertEqual(env["error"]["code"], "gate_not_met")
            self.assertIn("next", env["error"])
            self.assertTrue(env["error"]["next"],
                            "gate_not_met envelope should include next hints")
            # At least one hint should mention a search script (for sources_breadth)
            self.assertTrue(
                any("search_" in cmd for cmd in env["error"]["next"]),
                f"expected a search_* hint, got: {env['error']['next']}")


class SchemaMetadataTest(unittest.TestCase):
    def test_top_level_schema_has_cli_version(self) -> None:
        env = run_script("research_state.py", ["--schema"])
        self.assertIn("cli_version", env["data"])
        self.assertRegex(env["data"]["cli_version"], r"^\d+\.\d+\.\d+$")

    def test_subcommand_meta_includes_since_and_tier(self) -> None:
        env = run_script("research_state.py", ["--schema"])
        subs = env["data"]["subcommands"]
        # advance was added in 0.4.0
        self.assertIn("advance", subs)
        self.assertIn("meta", subs["advance"])
        self.assertEqual(subs["advance"]["meta"].get("since"), "0.4.0")
        # ingest has tier=write
        self.assertEqual(subs["ingest"]["meta"].get("tier"), "write")


if __name__ == "__main__":
    unittest.main()
