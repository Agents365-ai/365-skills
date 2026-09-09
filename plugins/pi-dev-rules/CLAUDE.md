# pi-dev-rules — local dev notes

- Mirror target: https://pi.dev/docs/latest
- Refresh cadence: weekly (Sundays) via `scripts/refresh.sh`
- Docs references: auto-built from GitHub source via `scripts/build-references.py`
- `references/philosophy-and-design.md` is MANUAL (creator's blog summary, Mario Zechner
  2025-11-30), NOT rebuilt by `refresh.sh`; edit it directly
- Changelog: auto-fetched from RSS via `scripts/fetch-changelog.py`
- License: MIT (docs content © Earendil Inc.)
- Version in SKILL.md frontmatter must stay in sync with Git tags
