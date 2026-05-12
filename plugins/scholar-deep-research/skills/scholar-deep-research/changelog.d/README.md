# Changelog fragments

Each pull request that affects observable behavior drops a small
markdown file here describing the change. At release time,
`towncrier build --version X.Y.Z` aggregates the fragments into
`../CHANGELOG.md` and deletes them.

This sidesteps the merge-conflict + diff-noise problem you get when
every PR hand-edits `CHANGELOG.md` directly.

## Fragment file naming

```
<short-kebab-slug>.<type>.md
```

- `<short-kebab-slug>` — anything unique to your PR. Convention:
  `ssrf-guard`, `docling-engine`, `rapidocr-lang`. No PR/issue numbers
  (we keep history in git, not in fragment filenames).
- `<type>` — one of: **feature**, **bugfix**, **doc**, **refactor**,
  **removal**. See `../towncrier.toml` for the canonical list.

Examples:

```
changelog.d/safe-get-ssrf-guard.feature.md
changelog.d/docling-num-pages-method.bugfix.md
changelog.d/agent-native-rubric-pass.refactor.md
```

## Fragment file body

One short sentence per fragment. Lead with the *user-visible* effect
(what changed for the agent calling the skill), not the implementation
detail. Compare:

- ✅ `extract_pdf.py now defaults to docling for scanned PDFs.`
- ❌ `Refactored _do_extract to thread engine kwarg through helper.`

For a bigger feature, multi-sentence is OK but keep it tight — readers
of `CHANGELOG.md` skim, they don't study.

## Release flow

```bash
# Dry-run to see what the next CHANGELOG.md will look like:
towncrier build --draft --version 0.15.0

# Write it for real (deletes fragments, edits CHANGELOG.md, no commit):
towncrier build --version 0.15.0

# Then bump metadata.version in SKILL.md and _common.py, commit, tag.
```

## When NOT to write a fragment

- Pure typo fixes in comments / docstrings
- Internal helper renames with no behavior change
- Test-only changes that don't change observable surface

For everything else — write the fragment. It costs 30 seconds.
