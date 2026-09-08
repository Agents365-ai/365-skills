# Changelog

## 0.7.2

- Fix install failure on Claude Code >= 2.1 (PR #26, thanks @Heelc). The
  plugin-manifest schema requires `commands` and `hooks` component paths to
  start with `./`; the bare paths were rejected with
  `hooks: Invalid input, commands: Invalid input`, so the plugin could not be
  installed at all. Every path in `plugins/pi/.claude-plugin/plugin.json` is
  now `./`-prefixed. Files and directory layout are unchanged.

## 0.7.1

- Pi 0.80.x compatibility:
  - `--effort max` is now accepted and forwarded via `set_thinking_level`
    (new top thinking level introduced in Pi 0.80.6; exposed by models such
    as GPT-5.6 and adaptive Claude).
  - `/pi:setup` readiness now recognizes credentials stored by pi `/login`
    in `~/.pi/agent/auth.json` (API keys and OAuth tokens). Previously a
    user authenticated only via `/login` was reported as "no provider
    configured" even though pi worked; the check looked at env vars and
    `models.json` alone. New `authProviderCount` field in the setup JSON.
- README value tier: suggest `kimi-k3` (Kimi K3 support landed in Pi 0.80.9).
- Includes the previously unreleased fixes from PR #24: untracked-symlink
  content leak in review prompts, race-worktree slug collision, and a
  job-state save race (`lib/git.mjs`, `lib/race.mjs`, `lib/state.mjs`).

## 0.7.0

- Incremental review: `/pi:review --incremental` (and `/pi:adversarial-review`)
  reviews only the commits since the last review on the current branch,
  instead of the full branch diff. A per-(workspace, branch) cache tracks the
  last-reviewed commit sha; after any successful review, HEAD is recorded as
  the new marker. Falls back to a full review when there is no valid cache
  (first run, or the cached commit is no longer an ancestor of HEAD after a
  rebase/history rewrite). Not combinable with `--base`; composes with
  `--models`/`--shards`. Only committed changes are covered — uncommitted
  working-tree changes are not part of the incremental diff. New
  `lib/review-cache.mjs` + `getHeadSha`/`isAncestor` in `lib/git.mjs`;
  8 new tests (205 total).

## 0.6.0

- `--out-file <path>` on `/pi:review`, `/pi:adversarial-review`, `/pi:rescue`,
  and `/pi:result` writes Pi's full output to a file and returns only a short
  summary (verdict, finding counts, one line per finding for reviews; a one-line
  summary for free-form task/rescue results). This keeps a large review or task
  result out of the calling agent's context to save tokens — relay the summary,
  open the file for detail. New `renderOutFileSummary`; 4 new tests (197 total).

## 0.5.0

- Sharded parallel review: `/pi:review --shards <N>` (and
  `/pi:adversarial-review`) splits the changed files across N review jobs
  that run in parallel — each job's diff is scoped to only its own files —
  then merges the findings (sorted by severity) into one review result.
  Activates only when `--shards` is 2 or more and more than one file
  changed; otherwise falls back to the normal single review. Not combinable
  with `--models`. New `lib/shard.mjs`; 11 new tests (193 total).

## 0.4.0

- Model racing: `/pi:rescue --race m1,m2,...` runs the same task with every
  listed model in parallel and presents each racer's result so a winner can
  be picked. Write races isolate each racer in its own git worktree created
  from HEAD (racers can never touch the user's tree or each other) and
  capture each racer's result as a patch — apply the winner with
  `git apply <patch>`. Read-only races present the answers side by side.
  Works foreground and `--background`; not combinable with `--model` or
  `--resume`. New `lib/race.mjs` + worktree helpers in `lib/git.mjs`;
  10 new tests (182 total) including a real-worktree integration test.

## 0.3.0

- Multi-model review panel: `/pi:review --models m1,m2,...` (and
  `/pi:adversarial-review`) reviews the same diff with several models in
  parallel and merges the findings — consensus findings (reported by 2+
  models) rank first with `found by:` tags; duplicates are matched per file
  with line-range slack, severity escalates to the highest reported, and
  alternate titles are preserved. A failed member (provider error, invalid
  JSON) is reported inline without sinking the panel.
- Automatic model fallback: set `PI_PLUGIN_FALLBACK_MODELS=a,b` and any
  failed review/task run is retried with the next model in the chain. The
  output ends with a `Model fallback:` note and the JSON payload carries
  `modelAttempts`. `/pi:setup` reports the configured chain.
- New lib modules `panel.mjs` and `fallback.mjs`; 41 new tests (172 total).

## 0.2.0

- pi-subagents integration: `/pi:setup` detects installation (npm + legacy paths)
  and lists agent profiles; rescue prompts gain subagent awareness; new
  `/pi:parallel-rescue` command for multi-task parallel fan-out via
  `subagent({ tasks: [...] })` (runs `task --write` so the subagent tool stays
  available).
- Test suite: 131 tests across process, git, state, JSON parsing, and args
  modules (`node --test`).
- Shell expansion safety fix (ported from upstream codex-plugin-cc):
  `shell: false` on git invocations.
- Fixed process-group kill that could take down the parent process
  (`detached: true` on pi spawn); fixed `auto_retry_end` failure deadlock;
  removed always-null `turnId`.
- `/pi:setup` shows pi version (min 0.75.0 check) and available models.
- Windows-safe `shellEscape`; renamed rescue agent to `pi-companion-forwarder`
  to prevent slash-command re-entry.
- Removed unimplemented `--background` flag from review commands; registered
  hooks/commands in plugin.json.
- Replace ASCII workflow diagram with drawio PNG; rephrase "1:1 fork" to
  "Adapted from".

## 0.1.2

- Model-agnostic: removed hard-coded `deepseek-v4-flash` / `deepseek-v4-pro` defaults
  that caused spawn failures for non-DeepSeek users.
- New env-var overrides: `PI_PLUGIN_REVIEW_MODEL` and
  `PI_PLUGIN_ADVERSARIAL_REVIEW_MODEL`. With nothing set, the plugin defers
  model selection entirely to pi.
- README rewritten as model-agnostic with a per-provider suggested-model table.

## 0.1.1

- Fixed 14 findings from a dual pi+DeepSeek self-review (3 critical, 2 high,
  6 medium, 3 low). Highlights: close()/agent_end deadlock fixes, SIGKILL
  escalation, stop-review-gate no longer silently bypasses when pi is
  unavailable, bounded stderr buffer, StringDecoder flush on close.

## 0.1.0

- Initial release of the Pi plugin for Claude Code, forked from `codex-plugin-cc`.
