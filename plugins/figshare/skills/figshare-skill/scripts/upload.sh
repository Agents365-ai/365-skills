#!/usr/bin/env bash
# Upload a file to a Figshare article using the 3-step multi-part flow.
# Usage: ./upload.sh <article_id> <file_path>
# Requires: FIGSHARE_TOKEN env var, curl, jq, md5sum (or md5 on macOS).
set -euo pipefail

ART="${1:?article_id required}"
FILE="${2:?file path required}"
: "${FIGSHARE_TOKEN:?FIGSHARE_TOKEN not set}"

API="https://api.figshare.com/v2"
AUTH=(-H "Authorization: token $FIGSHARE_TOKEN")

[ -f "$FILE" ] || { echo "file not found: $FILE" >&2; exit 1; }

NAME=$(basename "$FILE")
if stat -f%z "$FILE" >/dev/null 2>&1; then SIZE=$(stat -f%z "$FILE"); else SIZE=$(stat -c%s "$FILE"); fi
if command -v md5sum >/dev/null 2>&1; then MD5=$(md5sum "$FILE" | awk '{print $1}'); else MD5=$(md5 -q "$FILE"); fi

echo ">> initiating upload: name=$NAME size=$SIZE md5=$MD5"
INIT=$(curl -sS -X POST "$API/account/articles/$ART/files" "${AUTH[@]}" \
  -H "Content-Type: application/json" \
  -d "{\"md5\":\"$MD5\",\"name\":\"$NAME\",\"size\":$SIZE}")
LOC=$(echo "$INIT" | jq -r '.location')
[ "$LOC" != "null" ] || { echo "init failed: $INIT" >&2; exit 1; }

FILE_INFO=$(curl -sS "${AUTH[@]}" "$LOC")
UPLOAD_URL=$(echo "$FILE_INFO" | jq -r '.upload_url')
FILE_ID=$(echo "$FILE_INFO" | jq -r '.id')
echo ">> file_id=$FILE_ID upload_url=$UPLOAD_URL"

PARTS=$(curl -sS "${AUTH[@]}" "$UPLOAD_URL")
NPARTS=$(echo "$PARTS" | jq '.parts | length')
echo ">> uploading $NPARTS part(s)"

echo "$PARTS" | jq -c '.parts[]' | while read -r part; do
  NO=$(echo "$part" | jq -r '.partNo')
  START=$(echo "$part" | jq -r '.startOffset')
  END=$(echo "$part" | jq -r '.endOffset')
  LEN=$((END - START + 1))
  echo "   part $NO: bytes $START-$END ($LEN)"
  dd if="$FILE" bs=1 skip="$START" count="$LEN" status=none \
    | curl -sS -X PUT --data-binary @- "${AUTH[@]}" "$UPLOAD_URL/$NO" >/dev/null
done

echo ">> completing upload"
# Figshare returns 202 with an HTML body; we only care about the status code.
CODE=$(curl -sS -o /dev/null -w "%{http_code}" -X POST "${AUTH[@]}" "$API/account/articles/$ART/files/$FILE_ID")
if [ "$CODE" != "200" ] && [ "$CODE" != "202" ]; then
  echo "complete failed: HTTP $CODE" >&2; exit 1
fi
echo ">> done: file_id=$FILE_ID (HTTP $CODE)"
