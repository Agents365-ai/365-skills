# pi-durable-dev-rules reference builders

Maintainer tooling. Using the skill needs none of it: the files in `references/` are shipped as-is.

| File | Purpose |
| ---- | ------- |
| `refresh.sh` | Rebuilds the four vendored bundles from a local pi checkout. |
| `build-references.py` | Copies the source files listed in its `BUNDLES` map into `references/`, each with a header. |

```bash
bash scripts/refresh.sh /path/to/pi     # or: PI_REPO=/path/to/pi bash scripts/refresh.sh
```

| Bundle | Source file |
| ------ | ----------- |
| `references/durable-guide.md` | `packages/durable/README.md` |
| `references/durable-spec.md` | `packages/durable/docs/spec.md` |
| `references/pi-ai-models.md` | `packages/ai/README.md` |
| `references/codemode-sandbox.md` | `packages/codemode/README.md` |

Nothing is fetched over the network: the script reads a local checkout of
<https://github.com/earendil-works/pi>. Only the four bundles above are generated;
`durable-api.md`, `durable-runtime.md`, and `durable-recipes.md` are written by hand and are not
touched by the script. Those three carry the exact API signatures, runtime semantics, and code
patterns, so they must be re-read against the source whenever the package changes: walk every
exported entry point of `packages/durable/package.json` (`src/index.ts` and each subpath
`src/*/index.ts`), then the type files those re-export (`src/types.ts`,
`src/harness/types.ts`, `src/env/index.ts`), and update the affected sections plus the `metadata`
line in `SKILL.md`.

After a refresh, review the diff, then bump `version`, `metadata.fetched`, and
`metadata.piRevision` in `SKILL.md` plus the plugin version in the repo-root marketplace entry
before releasing.
