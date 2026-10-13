#!/usr/bin/env bash
# Rebuild every vendored reference bundle from a local Pi checkout.
#
# Requires the pi monorepo (https://github.com/earendil-works/pi) on disk.
# Nothing is fetched from the network.
#
# Usage: bash scripts/refresh.sh [/path/to/pi]
#        PI_REPO=/path/to/pi bash scripts/refresh.sh
#
# The checkout root comes from the first argument, then from PI_REPO, then from
# the directory the script was started in. The hand-written references
# (durable-api.md, durable-runtime.md, durable-recipes.md) are never touched.
set -euo pipefail

START_DIR="$PWD"
cd "$(dirname "$0")/.."

PI_REPO="${1:-${PI_REPO:-$START_DIR}}"
if [ ! -f "$PI_REPO/packages/durable/README.md" ]; then
	echo "not a Pi checkout: $PI_REPO" >&2
	echo "pass the pi monorepo root, for example:" >&2
	echo "  bash scripts/refresh.sh /path/to/pi" >&2
	exit 1
fi

REV=$(git -C "$PI_REPO" rev-parse --short HEAD 2>/dev/null || echo unknown)
VERSION=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' \
	"$PI_REPO/packages/durable/package.json")

echo "=== Reference bundles (pi@$REV, pi-durable $VERSION) ==="
python3 scripts/build-references.py "$PI_REPO"
echo ""

echo "Done. Review the diff, then update version, metadata.fetched, and metadata.piRevision"
echo "in SKILL.md, commit on a feature branch, and tag a release:"
echo "  git checkout -b refresh-\$(date +%Y-%m-%d)"
echo "  git add references/ && git commit -m 'Refresh references (pi@$REV)'"
