#!/usr/bin/env python3
"""check_update.py — check for and apply skill updates.

Runs once per 24 hours at Phase 0 Step 0. Fast-forwards the skill's git
checkout against its upstream remote when an update is available, and
surfaces what happened through the standard JSON envelope so SKILL.md
can tell the user in one line.

The throttle (24h, via `.last_update_check` timestamp in the skill
root) mirrors the asta-skill pattern: a research session should not
spend a network round-trip every single time the skill activates —
daily is enough for git fast-forwards, and the user can always pass
`--force` to bypass the throttle when they know something upstream
changed.

Design constraints (see CLAUDE.md, "The CLI contract"):
  - Never fails the workflow. Any error (offline, no remote, dirty tree,
    non-git install) becomes a structured envelope with exit 0.
  - Respects SCHOLAR_SKIP_UPDATE_CHECK=1 as an opt-out escape hatch for
    users who want to pin a version.
  - Honors --ff-only semantics: local modifications are never clobbered.
    When the working tree is dirty the update is skipped and the user is
    informed, so they know auto-update did not run.
  - Does not pip-install. Detects requirements.txt drift and surfaces a
    hint; the host environment (which venv, which python) is the user's
    to manage, not this script's.
  - The only script in this repo allowed to touch the skill's own files.

Action values:
  up_to_date         local HEAD == upstream HEAD
  updated            fast-forward pull succeeded
  update_available   --dry-run only; pull would succeed
  skipped_dirty      working tree has uncommitted changes
  skipped_disabled   SCHOLAR_SKIP_UPDATE_CHECK is set
  skipped_throttled  last check was within the 24h throttle window
  not_a_git_repo     installed without .git (tarball, package manager)
  check_failed       git/network error; `reason` field explains
"""
from __future__ import annotations

import argparse
import os
import subprocess
import time
from pathlib import Path

from _common import maybe_emit_schema, ok

SKILL_ROOT = Path(__file__).resolve().parent.parent

# 24-hour throttle window. The file stores a unix timestamp (float). Any
# terminal action other than `check_failed` bumps the stamp; `check_failed`
# leaves it alone so a transient failure (offline, rate-limit) is retried
# on the next invocation rather than silently suppressed for a day.
THROTTLE_FILE = SKILL_ROOT / ".last_update_check"
THROTTLE_WINDOW_S = 24 * 60 * 60


def throttle_age_s() -> float | None:
    """Seconds since the last check, or None if the file is missing/bad."""
    try:
        stamp = float(THROTTLE_FILE.read_text().strip())
    except (OSError, ValueError):
        return None
    return time.time() - stamp


def bump_throttle() -> None:
    """Record the current wall-clock time into the throttle file."""
    try:
        THROTTLE_FILE.write_text(f"{time.time():.0f}\n")
    except OSError:
        # A read-only install (unusual — implies the whole skill dir is
        # read-only) shouldn't prevent the workflow from continuing.
        pass


def run_git(*args: str) -> tuple[int, str, str]:
    """Run a git command in the skill root. Returns (rc, stdout, stderr)."""
    try:
        p = subprocess.run(
            ["git", *args],
            cwd=str(SKILL_ROOT),
            capture_output=True,
            text=True,
            timeout=20,
        )
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return 128, "", str(e)


def is_git_repo() -> bool:
    return (SKILL_ROOT / ".git").exists()


def local_head() -> str | None:
    rc, out, _ = run_git("rev-parse", "HEAD")
    return out if rc == 0 and out else None


def upstream_head() -> str | None:
    """HEAD of the upstream tracking branch after fetch."""
    rc, out, _ = run_git("rev-parse", "@{u}")
    return out if rc == 0 and out else None


def fetch() -> tuple[bool, str]:
    rc, _, stderr = run_git("fetch", "--quiet", "origin")
    return rc == 0, stderr


def dirty_files() -> list[str]:
    rc, out, _ = run_git("status", "--porcelain")
    if rc != 0:
        return []
    return [line[3:] for line in out.splitlines() if line]


def commits_behind(local: str, upstream: str) -> int | None:
    rc, out, _ = run_git("rev-list", "--count", f"{local}..{upstream}")
    return int(out) if rc == 0 and out.isdigit() else None


def requirements_changed(old: str, new: str) -> bool:
    rc, out, _ = run_git("diff", "--name-only", old, new,
                         "--", "requirements.txt")
    return rc == 0 and bool(out.strip())


def commits_summary(old: str, new: str, *, limit: int = 5) -> list[str]:
    """Subjects of feat/fix commits in (old, new], newest first, capped at
    `limit`. Returns [] on any git failure — degrade-silent so a broken log
    never blocks the update from reporting success.
    """
    rc, out, _ = run_git(
        "log", "--no-merges",
        "--pretty=format:%s",
        "-E", "--grep=^(feat|fix)",
        f"{old}..{new}",
    )
    if rc != 0 or not out:
        return []
    return out.splitlines()[:limit]


def fast_forward() -> tuple[bool, str]:
    rc, _, stderr = run_git("pull", "--ff-only", "--quiet")
    return rc == 0, stderr


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Check for and apply updates to the scholar-deep-research "
            "skill. Always exits 0; the action field describes what "
            "happened. Self-throttles to once per 24 hours; pass --force "
            "to bypass."
        )
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Check for updates but do not pull")
    parser.add_argument("--force", action="store_true",
                        help="Bypass the 24h throttle window — always "
                             "perform the fetch/check even if the last "
                             "check was recent.")
    maybe_emit_schema(parser, "check_update")
    args = parser.parse_args()

    # Opt-out escape hatch — the user pinned a version on purpose.
    if os.environ.get("SCHOLAR_SKIP_UPDATE_CHECK"):
        ok({"action": "skipped_disabled",
            "reason": "SCHOLAR_SKIP_UPDATE_CHECK is set"})
        bump_throttle()
        return

    # 24h throttle — a research session reactivating the skill every few
    # minutes shouldn't burn a git fetch every time. --force overrides for
    # manual/testing runs. --dry-run always checks (it doesn't mutate).
    if not args.force and not args.dry_run:
        age = throttle_age_s()
        if age is not None and age < THROTTLE_WINDOW_S:
            ok({"action": "skipped_throttled",
                "reason": (f"Last check was {int(age)}s ago; throttle "
                           f"window is {THROTTLE_WINDOW_S}s. Pass --force "
                           f"to re-check now."),
                "next_check_in_s": int(THROTTLE_WINDOW_S - age)})
            return

    # Non-git install (ClawHub tarball, SkillsMP package, vendored copy).
    # The package manager owns updates for this install — we should not.
    if not is_git_repo():
        ok({"action": "not_a_git_repo",
            "reason": ("No .git directory — skill is managed by a package "
                       "manager. Use its own update command."),
            "skill_root": str(SKILL_ROOT)})
        bump_throttle()
        return

    local = local_head()
    if not local:
        ok({"action": "check_failed",
            "reason": "Could not read local HEAD"})
        return

    # One network call: fetch objects so we can diff locally afterwards.
    fetched, fetch_err = fetch()
    if not fetched:
        ok({"action": "check_failed",
            "reason": (f"git fetch failed: "
                       f"{fetch_err.splitlines()[0] if fetch_err else 'unknown error'}"),
            "local_head": local[:12]})
        return

    upstream = upstream_head()
    if not upstream:
        ok({"action": "check_failed",
            "reason": ("No upstream tracking branch configured "
                       "(e.g. 'git branch --set-upstream-to=origin/main')"),
            "local_head": local[:12]})
        return

    if local == upstream:
        ok({"action": "up_to_date", "head": local[:12]})
        bump_throttle()
        return

    behind = commits_behind(local, upstream)
    reqs_changed = requirements_changed(local, upstream)

    # Protect local modifications. --ff-only would already refuse, but we
    # catch it earlier so the user gets a structured reason instead of a
    # raw git error.
    dirty = dirty_files()
    if dirty:
        ok({"action": "skipped_dirty",
            "reason": ("Local modifications present — auto-update will "
                       "not clobber your work"),
            "dirty_files": dirty[:5],
            "dirty_count": len(dirty),
            "local_head": local[:12],
            "remote_head": upstream[:12],
            "commits_behind": behind,
            "requirements_changed": reqs_changed,
            "hint": f"Review: cd {SKILL_ROOT} && git status"})
        bump_throttle()
        return

    if args.dry_run:
        # Dry-run does not mutate state and does not write throttle —
        # the caller is explicitly previewing, a real check should still
        # follow on its normal schedule.
        ok({"action": "update_available",
            "dry_run": True,
            "from": local[:12],
            "to": upstream[:12],
            "commits_behind": behind,
            "requirements_changed": reqs_changed})
        return

    success, stderr = fast_forward()
    if not success:
        ok({"action": "check_failed",
            "reason": (f"git pull --ff-only failed: "
                       f"{stderr.splitlines()[0] if stderr else 'unknown'}"),
            "local_head": local[:12],
            "remote_head": upstream[:12]})
        return

    data: dict = {
        "action": "updated",
        "from": local[:12],
        "to": upstream[:12],
        "commits_behind": behind,
        "requirements_changed": reqs_changed,
    }
    what_changed = commits_summary(local, upstream)
    if what_changed:
        data["what_changed"] = what_changed
    if reqs_changed:
        data["hint"] = ("Python dependencies changed — run "
                        "`pip install -r requirements.txt` before the "
                        "next invocation")
    ok(data)
    bump_throttle()


if __name__ == "__main__":
    main()
