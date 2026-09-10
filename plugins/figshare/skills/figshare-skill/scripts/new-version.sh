#!/usr/bin/env bash
# Create a new version of a published Figshare article by reserving a version
# and uploading a new file. Published versions are frozen, so edits require
# a new version.
#
# Usage: ./new-version.sh <article_id> <file_path>
# Requires: FIGSHARE_TOKEN, curl, jq, and scripts/upload.sh next to this file.
set -euo pipefail

ART="${1:?article_id required}"
FILE="${2:?file path required}"
: "${FIGSHARE_TOKEN:?FIGSHARE_TOKEN not set}"

API="https://api.figshare.com/v2"
AUTH=(-H "Authorization: token $FIGSHARE_TOKEN")
HERE="$(cd "$(dirname "$0")" && pwd)"

echo ">> reserving new version for article $ART"
# Reserving a DOI on the next version creates a pending draft you can edit.
curl -sS -X POST "${AUTH[@]}" "$API/account/articles/$ART/reserve_doi" >/dev/null || true

echo ">> uploading $FILE to article $ART (draft version)"
bash "$HERE/upload.sh" "$ART" "$FILE"

echo ">> publishing new version"
curl -sS -o /dev/null -w "publish status: %{http_code}\n" \
  -X POST "${AUTH[@]}" "$API/account/articles/$ART/publish"
