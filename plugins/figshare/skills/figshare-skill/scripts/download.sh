#!/usr/bin/env bash
# Download all files from a public Figshare article.
# Usage: ./download.sh <article_id|figshare_url> [output_dir]
set -euo pipefail

ARG="${1:?article_id or figshare URL required}"
OUT="${2:-.}"
mkdir -p "$OUT"

# Accept a figshare.com URL and extract the numeric id from the tail.
ART=$(echo "$ARG" | grep -oE '[0-9]+' | tail -1)
[ -n "$ART" ] || { echo "could not parse article id from: $ARG" >&2; exit 1; }

echo ">> article $ART"
curl -sS "https://api.figshare.com/v2/articles/$ART/files" \
  | jq -r '.[] | "\(.download_url)\t\(.name)"' \
  | while IFS=$'\t' read -r url name; do
      echo "   downloading $name"
      curl -L -sS -o "$OUT/$name" "$url"
    done
echo ">> done -> $OUT"
