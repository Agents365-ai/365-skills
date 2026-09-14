# pi-dev-rules reference builders

Maintainer tooling. Using the skill needs none of this: the generated files in `references/` are
shipped as-is.

| File | Purpose |
| ---- | ------- |
| `refresh.sh` | Rebuilds every reference bundle and `changelog.md` from a pi checkout. |
| `build-references.py` | Concatenates the source docs listed in its `BUNDLES` map. |
| `build-changelog.py` | Renders the release table from `packages/coding-agent/CHANGELOG.md`. |

```bash
bash scripts/refresh.sh /path/to/pi     # or: PI_REPO=/path/to/pi bash scripts/refresh.sh
```

Nothing is fetched over the network: the script reads a local checkout of
<https://github.com/earendil-works/pi>. That checkout holds the same pages that back
<https://pi.dev/docs/latest>, so the coding-agent bundles stay identical to the published site.

`changelog.md` records the revision it was built from. After a refresh, review the diff, then bump
`version`, `metadata.fetched`, and `metadata.piRevision` in `SKILL.md` plus the plugin version in
the repo-root marketplace entry before releasing.

`references/philosophy-and-design.md` is curated by hand and is not touched by the scripts.
