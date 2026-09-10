# End-to-end examples

All examples assume:
```bash
export ZENODO_TOKEN=...
export ZENODO_BASE=https://sandbox.zenodo.org/api   # use https://zenodo.org/api for production
```

## 1. Upload a dataset and publish

```bash
#!/usr/bin/env bash
set -euo pipefail

# 1. Create empty deposition
RESP=$(curl -sS -X POST "$ZENODO_BASE/deposit/depositions" \
  -H "Authorization: Bearer $ZENODO_TOKEN" \
  -H "Content-Type: application/json" -d '{}')
DEPOSIT_ID=$(echo "$RESP" | jq -r .id)
BUCKET=$(echo "$RESP" | jq -r .links.bucket)
echo "Deposition $DEPOSIT_ID, bucket $BUCKET"

# 2. Upload all files in ./data/
for f in ./data/*; do
  name=$(basename "$f")
  curl -sS --upload-file "$f" \
    -H "Authorization: Bearer $ZENODO_TOKEN" \
    "$BUCKET/$name" > /dev/null
  echo "uploaded $name"
done

# 3. Set metadata
curl -sS -X PUT "$ZENODO_BASE/deposit/depositions/$DEPOSIT_ID" \
  -H "Authorization: Bearer $ZENODO_TOKEN" \
  -H "Content-Type: application/json" \
  -d @metadata.json

# 4. Review (don't publish blindly)
curl -sS "$ZENODO_BASE/deposit/depositions/$DEPOSIT_ID" \
  -H "Authorization: Bearer $ZENODO_TOKEN" | jq '.metadata, .files[].filename'

read -p "Publish? [y/N] " ok
[[ "$ok" == "y" ]] || { echo "aborted"; exit 0; }

# 5. Publish
curl -sS -X POST "$ZENODO_BASE/deposit/depositions/$DEPOSIT_ID/actions/publish" \
  -H "Authorization: Bearer $ZENODO_TOKEN" | jq '{doi, links: .links.record_html}'
```

## 2. Publish a new version

```bash
PARENT_ID=1234567   # the previous deposition id

# Create new version draft
NEW=$(curl -sS -X POST "$ZENODO_BASE/deposit/depositions/$PARENT_ID/actions/newversion" \
  -H "Authorization: Bearer $ZENODO_TOKEN")

# Follow latest_draft link to get the new draft id + bucket
DRAFT_URL=$(echo "$NEW" | jq -r .links.latest_draft)
DRAFT=$(curl -sS "$DRAFT_URL" -H "Authorization: Bearer $ZENODO_TOKEN")
NEW_ID=$(echo "$DRAFT" | jq -r .id)
BUCKET=$(echo "$DRAFT" | jq -r .links.bucket)

# Optional: delete an inherited file you want to replace
curl -sS -X DELETE "$BUCKET/old-data.csv" -H "Authorization: Bearer $ZENODO_TOKEN"

# Upload new file
curl -sS --upload-file ./new-data.csv \
  -H "Authorization: Bearer $ZENODO_TOKEN" "$BUCKET/new-data.csv"

# Update version string in metadata
curl -sS -X PUT "$ZENODO_BASE/deposit/depositions/$NEW_ID" \
  -H "Authorization: Bearer $ZENODO_TOKEN" -H "Content-Type: application/json" \
  -d '{"metadata": {"version": "v1.1.0", "title": "...", "upload_type": "dataset", "description": "...", "creators": [...]}}'

# Publish
curl -sS -X POST "$ZENODO_BASE/deposit/depositions/$NEW_ID/actions/publish" \
  -H "Authorization: Bearer $ZENODO_TOKEN"
```

Note: when calling PUT on metadata for a new version, you must include the **full** metadata object (not just the changed fields).

## 3. Software release tied to a GitHub tag

The recommended path is the [Zenodo–GitHub integration](https://docs.github.com/en/repositories/archiving-a-github-repository/referencing-and-citing-content) — enable the repo in Zenodo settings and create a GitHub release; Zenodo auto-archives.

If doing it via API instead, use upload_type `software` and put the GitHub tag URL in `related_identifiers` with relation `isSupplementTo`. See `metadata.md` for the JSON shape.

## 4. List your own depositions

```bash
curl -sS "$ZENODO_BASE/deposit/depositions?status=draft&size=25" \
  -H "Authorization: Bearer $ZENODO_TOKEN" | jq '.[] | {id, title: .title, state}'
```

## 5. Download files from a public record

```bash
REC=1234567
curl -sS "$ZENODO_BASE/records/$REC" | jq -r '.files[].links.self' | \
  xargs -n1 curl -sS -LO
```
