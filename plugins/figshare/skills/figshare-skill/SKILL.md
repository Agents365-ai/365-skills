---
name: figshare-skill
description: Use whenever the user wants to interact with Figshare - searching public datasets/articles, downloading Figshare files, listing their own articles/collections/projects, creating or updating articles, or uploading files (including large multi-part uploads) via the Figshare v2 REST API. Trigger on mentions of "figshare", figshare DOIs (10.6084/m9.figshare.*), figshare.com URLs, or phrases like "upload my dataset to figshare", "publish to figshare", "get figshare article".
homepage: https://github.com/Agents365-ai/365-skills
license: MIT
---

# Figshare Skill

Interact with the [Figshare v2 REST API](https://docs.figshare.com/) to search, download, create, and upload research outputs.

## Prerequisites

- `curl` and `jq` available on PATH.
- For authenticated endpoints (anything under `/account/...` or uploads), a **personal token** from <https://figshare.com/account/applications> exported as:

  ```bash
  export FIGSHARE_TOKEN=xxxxxxxxxxxxxxxx
  ```

- Public endpoints (search, public articles, downloads) need no token.

Always confirm with the user before creating, modifying, publishing, or deleting anything on their account — these are hard to reverse.

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

## API Basics

- **Base URL:** `https://api.figshare.com/v2`
- **Auth header:** `Authorization: token $FIGSHARE_TOKEN`
- **Content-Type:** `application/json` for POST/PUT bodies
- **Rate limit:** keep it under ~1 request/second to avoid abuse throttling
- **Errors:** JSON body with `message`, `code`; common codes 400/401/403/404/422

## Common Recipes

### Search public articles

```bash
curl -s -X POST https://api.figshare.com/v2/articles/search \
  -H "Content-Type: application/json" \
  -d '{"search_for": ":title: single cell", "page_size": 20}' | jq
```

Field operators: `:title:`, `:author:`, `:tag:`, `:category:`, `:doi:`, `:resource_doi:`.

### Get a public article (by ID or DOI)

```bash
curl -s https://api.figshare.com/v2/articles/{article_id} | jq
# or resolve from a figshare.com URL: the numeric tail is the article_id
```

### Download all files from a public article

```bash
ART=12345678
curl -s https://api.figshare.com/v2/articles/$ART/files \
  | jq -r '.[] | "\(.download_url)\t\(.name)"' \
  | while IFS=$'\t' read -r url name; do curl -L -o "$name" "$url"; done
```

### List your own articles

```bash
curl -s -H "Authorization: token $FIGSHARE_TOKEN" \
  "https://api.figshare.com/v2/account/articles?page=1&page_size=50" | jq
```

### Create an article (draft)

```bash
curl -s -X POST https://api.figshare.com/v2/account/articles \
  -H "Authorization: token $FIGSHARE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My dataset",
    "description": "Full description here.",
    "defined_type": "dataset",
    "tags": ["demo"],
    "categories": [2]
  }' | jq
```

Response is `{ "location": ".../account/articles/{id}", "entity_id": 123 }`.

### Update / publish an article

```bash
# update metadata
curl -s -X PUT https://api.figshare.com/v2/account/articles/$ART \
  -H "Authorization: token $FIGSHARE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "New title"}'

# publish (becomes public, assigns DOI, version is frozen)
curl -s -X POST https://api.figshare.com/v2/account/articles/$ART/publish \
  -H "Authorization: token $FIGSHARE_TOKEN"
```

Always ask before publishing — it's permanent for that version.

### Collections & projects

```bash
# create collection that groups existing articles
curl -s -X POST https://api.figshare.com/v2/account/collections \
  -H "Authorization: token $FIGSHARE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "My Collection", "articles": [123, 456]}'

# create project
curl -s -X POST https://api.figshare.com/v2/account/projects \
  -H "Authorization: token $FIGSHARE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Research Project"}'
```

## Uploading Files (Multi-part Flow)

Figshare uploads are **3-step**: initiate → PUT each part → complete. Use the bundled helpers for anything non-trivial:

```bash
# upload a file to an existing draft article
./scripts/upload.sh <article_id> <path/to/file>

# batch-download every file from a public article (accepts id or figshare.com URL)
./scripts/download.sh <article_id_or_url> [output_dir]

# reserve + upload + publish a new version of an already-published article
./scripts/new-version.sh <article_id> <path/to/file>
```

The raw flow, in case you need to adapt it:

1. **Initiate** — compute md5 + size, POST to article:

   ```bash
   SIZE=$(stat -f%z "$FILE" 2>/dev/null || stat -c%s "$FILE")
   MD5=$(md5sum "$FILE" | awk '{print $1}')   # or: md5 -q on macOS
   curl -s -X POST https://api.figshare.com/v2/account/articles/$ART/files \
     -H "Authorization: token $FIGSHARE_TOKEN" \
     -H "Content-Type: application/json" \
     -d "{\"md5\":\"$MD5\",\"name\":\"$(basename $FILE)\",\"size\":$SIZE}"
   ```

   Response has `location` pointing at `/account/articles/$ART/files/$FILE_ID`.

2. **Fetch upload info** from that file record — it contains an `upload_url`. GET the upload_url to learn the part layout (`parts: [{partNo, startOffset, endOffset}]`).

3. **Upload parts** — for each part, PUT the byte range to `${upload_url}/${partNo}`:

   ```bash
   dd if="$FILE" bs=1 skip=$START count=$((END-START+1)) 2>/dev/null \
     | curl -s -X PUT --data-binary @- "${upload_url}/${partNo}" \
       -H "Authorization: token $FIGSHARE_TOKEN"
   ```

4. **Complete** — POST to the file record to finalize:

   ```bash
   curl -s -X POST https://api.figshare.com/v2/account/articles/$ART/files/$FILE_ID \
     -H "Authorization: token $FIGSHARE_TOKEN"
   ```

Why three steps: Figshare streams large files through a separate upload service. Skipping the complete call leaves the file in a pending state and it won't appear on the article.

## Pagination

Most list endpoints accept either `page`+`page_size` or `limit`+`offset`. Max `page_size` is typically 1000. For large harvests, loop until an empty page:

```bash
page=1
while :; do
  out=$(curl -s "https://api.figshare.com/v2/articles?page=$page&page_size=100")
  [ "$(echo "$out" | jq 'length')" = "0" ] && break
  echo "$out" | jq -c '.[]'
  page=$((page+1))
  sleep 1
done
```

## Troubleshooting

- **401** — token missing/expired; re-check `$FIGSHARE_TOKEN`.
- **403** on `/account/...` — token lacks the needed scope; regenerate with full permissions.
- **422** on article create — missing required field (usually `title`) or bad `categories`/`defined_type`.
- **Upload parts mismatch** — md5 or size in step 1 didn't match the bytes actually uploaded; recompute and restart.
- **Published article won't update** — publishing freezes a version; create a new version instead.

## References

- API reference: <https://docs.figshare.com/>
- Token management: <https://figshare.com/account/applications>
- Category IDs: `GET https://api.figshare.com/v2/categories`
- License IDs: `GET https://api.figshare.com/v2/licenses`
