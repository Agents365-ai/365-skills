# Task progress

Refresh pi-dev-rules from Pi 1.3.0 (pi@71023aec1) to 1.5.0 (pi@f9a263655).

- [x] Fetch upstream tags; v1.5.0 is the latest release and its docs tree matches origin/main.
- [x] Build a throwaway worktree at v1.5.0; diff the docs and bundle sources against v1.3.0.
- [x] Add `docs/models-configuration.md` to the provider bundle; note the Chord v2 tree in the
      chord header (design docs in `packages/chord/docs/next`, not bundled).
- [x] Rebuild 15 bundles and `changelog.md` (291 release sections).
- [x] Update `durable.md`: version table to 1.5.0, watch/view API changes, 38 examples, 6531-line spec.
- [x] Bump SKILL.md to 0.10.0 (docVersion 1.5.0, fetched 2026-11-02, piRevision f9a263655) and
      refresh the reference index, update notes, and hard rules (pi-schema validation).
- [x] Update bilingual READMEs and the marketplace version.
- [x] Verify determinism (identical hashes over `references/*.md`), `py_compile`, Ruff, JSON.
- [x] Regenerate the SkillSpector baseline (20 suppressed doc-prose fingerprints) and confirm the
      scan reports 0 issues.
- [x] Remove the temporary upstream worktree.
- [ ] Commit on a feature branch and open a PR (user permission pending).

Preserve unrelated changes: the pre-existing `disable-model-invocation: true` line in SKILL.md, the
untracked `pi-rules-pr.log*` files in the repository root.
