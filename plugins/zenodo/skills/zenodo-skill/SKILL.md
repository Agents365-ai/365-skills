---
name: zenodo-skill
description: Use whenever the user mentions Zenodo, depositing or publishing research artifacts (datasets, software, papers, posters) to Zenodo, minting a DOI for a dataset/code release, uploading files to a Zenodo record, creating a new version of a Zenodo deposit, or searching Zenodo records. Covers the full Zenodo REST API workflow — create deposition, upload files via the bucket API, set metadata, publish, version, and search — for both production (zenodo.org) and sandbox (sandbox.zenodo.org).
license: MIT
homepage: https://github.com/Agents365-ai/365-skills
platforms: [macos, linux, windows]
metadata: {"openclaw":{"requires":{"bins":["curl"],"env":["ZENODO_TOKEN"]},"emoji":"📦","os":["darwin","linux","win32"]},"hermes":{"tags":["zenodo","doi","dataset","research-data","open-science","preprint","publishing"],"category":"research","requires_tools":["curl"],"related_skills":["zotero-manager","semanticscholar-skill"]},"author":"Agents365-ai","version":"1.0.0"}
---

# Zenodo Skill

Interact with the [Zenodo REST API](https://developers.zenodo.org) to deposit, publish, version, and search research artifacts. Zenodo issues a citable DOI for every published record.

## When to use

- User wants to upload a dataset, code release, paper, poster, or other artifact to Zenodo
- User wants a DOI for a research output
- User wants to update an existing deposit or publish a new version
- User wants to search Zenodo for records

## Update check

Throttle to one check per 24 hours per installation; never mutate the skill directory without explicit user consent.

1. If `<this-skill-dir>/.last_update` exists and is less than 24 hours old, skip this step entirely.

2. Otherwise, fetch the latest tag from upstream:

   ```bash
   git -C <this-skill-dir> ls-remote --tags origin 'v*' 2>/dev/null \
     | awk '{print $2}' | sed 's|refs/tags/||' \
     | sort -V | tail -1
   ```

3. Compare with this skill's `metadata.version` from the frontmatter. If the upstream tag is strictly newer (semver), tell the user one line and ask:

   > "A newer version of this skill is available: vX.Y.Z → vA.B.C. Want me to `git pull`?"

   If they say yes, run `git -C <this-skill-dir> pull --ff-only`. Refresh `.last_update` either way so the prompt doesn't repeat for 24 hours.

4. If upstream is the same or older, refresh `.last_update` silently and continue.

5. On any failure (offline, not a git checkout — e.g. ClawHub-installed copy, read-only path, no permission), swallow the error silently and continue with the user's task. Do not mention the failure.

## Setup

Two environments — pick one and stick with it during a session:

| Env | Base URL | Token page |
|---|---|---|
| Production | `https://zenodo.org/api` | https://zenodo.org/account/settings/applications/tokens/new/ |
| Sandbox (testing) | `https://sandbox.zenodo.org/api` | https://sandbox.zenodo.org/account/settings/applications/tokens/new/ |

Sandbox accounts/tokens are **separate** from production. Always test new workflows in sandbox first — published production records cannot be deleted.

Required token scopes: `deposit:write` and `deposit:actions`.

Export the token before running commands:
```bash
export ZENODO_TOKEN=...        # never inline the token in commands you show the user
export ZENODO_BASE=https://sandbox.zenodo.org/api   # or https://zenodo.org/api
```

If `ZENODO_TOKEN` is unset, ask the user for it (and which environment) before proceeding.

## Core workflow: deposit a new artifact

The deposit lifecycle is **create → upload files → set metadata → publish**. Each step is a separate API call; do them in order.

### 1. Create an empty deposition

```bash
curl -sS -X POST "$ZENODO_BASE/deposit/depositions" \
  -H "Authorization: Bearer $ZENODO_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

The response JSON contains two things you need to remember:
- `id` — the deposition id, used for metadata/publish/version actions
- `links.bucket` — the bucket URL for file uploads (new files API)

Capture them, e.g. with `jq`:
```bash
RESP=$(curl -sS -X POST "$ZENODO_BASE/deposit/depositions" \
  -H "Authorization: Bearer $ZENODO_TOKEN" -H "Content-Type: application/json" -d '{}')
DEPOSIT_ID=$(echo "$RESP" | jq -r .id)
BUCKET=$(echo "$RESP" | jq -r .links.bucket)
```

### 2. Upload files (bucket API — preferred)

The bucket API supports up to 50 GB total / 100 files per record. Use `--upload-file` (HTTP PUT) — **not** multipart form upload. The filename in the URL is what shows up on the record.

```bash
curl -sS --upload-file ./data.csv \
  -H "Authorization: Bearer $ZENODO_TOKEN" \
  "$BUCKET/data.csv"
```

Repeat per file. For many files, loop in shell. The legacy `/files` multipart endpoint is capped at 100 MB/file — avoid it.

### 3. Set metadata

Metadata goes via `PUT` on the deposition. **Required** fields: `upload_type`, `title`, `creators`, `description`. See `references/metadata.md` for the full schema, allowed `upload_type` values, license codes, and conditional fields (e.g. `publication_type`, `embargo_date`).

Minimal example:
```bash
curl -sS -X PUT "$ZENODO_BASE/deposit/depositions/$DEPOSIT_ID" \
  -H "Authorization: Bearer $ZENODO_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "metadata": {
      "title": "My dataset",
      "upload_type": "dataset",
      "description": "<p>A short description (HTML allowed).</p>",
      "creators": [{"name": "Doe, Jane", "affiliation": "Example Univ.", "orcid": "0000-0002-1825-0097"}]
    }
  }'
```

Read the response — Zenodo validates here and returns 400 with field-level errors if anything is missing or malformed. Fix and retry before publishing.

### 4. Publish

**Publishing is irreversible on production** (you can edit metadata later but cannot remove files or delete the record). Confirm with the user before this step unless they're on sandbox.

```bash
curl -sS -X POST "$ZENODO_BASE/deposit/depositions/$DEPOSIT_ID/actions/publish" \
  -H "Authorization: Bearer $ZENODO_TOKEN"
```

The response contains `doi` and `links.record_html` — show both to the user.

## New version of an existing record

Use this when the user has previously published and wants to release updated data/code under the same concept-DOI.

```bash
# 1. Create new version draft (returns links.latest_draft)
curl -sS -X POST "$ZENODO_BASE/deposit/depositions/$DEPOSIT_ID/actions/newversion" \
  -H "Authorization: Bearer $ZENODO_TOKEN"
```

Then follow the bucket of the new draft (from `links.latest_draft` → GET it → use its `links.bucket`) to upload changed files, update metadata, and publish as in steps 2–4 above. The new version inherits files from the previous version by default — delete any you want to replace via `DELETE $BUCKET/<filename>`.

## Discard a draft

```bash
curl -sS -X POST "$ZENODO_BASE/deposit/depositions/$DEPOSIT_ID/actions/discard" \
  -H "Authorization: Bearer $ZENODO_TOKEN"
```

## Search published records

No token needed for public search.
```bash
curl -sS "$ZENODO_BASE/records?q=climate+model&size=10&sort=mostrecent"
```

Query syntax is Elasticsearch — fielded queries like `creators.name:"Doe, Jane"`, `communities:zenodo`, `resource_type.type:dataset` all work. See `references/search.md` for query patterns.

## Conventions and gotchas

- **Always check HTTP status.** 201 = created, 202 = publish accepted, 400 = metadata error (read the body), 401 = bad token, 403 = wrong scope, 429 = rate limited.
- **Rate limits:** 100 req/min, 5000 req/hour for authenticated users. Watch `X-RateLimit-Remaining`.
- **Never inline the token** in commands you display — use `$ZENODO_TOKEN`. Don't write the token to files.
- **Sandbox first.** Suggest sandbox for any first-time workflow; switch to production only when the user explicitly confirms.
- **Verify before publishing.** GET the deposition and review files + metadata with the user before calling `actions/publish` on production.
- **Large uploads:** for files > a few hundred MB, consider doing the curl upload with `--progress-bar` and warn the user about time/bandwidth.

## References

- `references/metadata.md` — full metadata schema, upload_type values, license codes, conditional fields
- `references/search.md` — search query syntax and useful filters
- `references/examples.md` — end-to-end shell scripts for common scenarios (dataset upload, software release, new version)
