#!/usr/bin/env bash
# Rebuild the reference bundles and the changelog from a local Pi checkout.
#
# Requires the pi monorepo (https://github.com/earendil-works/pi) on disk.
# Nothing is fetched from the network.
#
# Usage: PI_REPO=/path/to/pi bash scripts/refresh.sh
#        PI_REPO defaults to ~/github/pi
#
# Intended cadence: weekly, since Pi releases ship every few days.
set -euo pipefail
cd "$(dirname "$0")/.."

PI_REPO="${PI_REPO:-$HOME/github/pi}"
if [ ! -d "$PI_REPO/packages/coding-agent/docs" ]; then
	echo "not a Pi checkout: $PI_REPO" >&2
	echo "set PI_REPO to the pi monorepo root, for example:" >&2
	echo "  PI_REPO=\$HOME/github/pi bash scripts/refresh.sh" >&2
	exit 1
fi

REV=$(git -C "$PI_REPO" rev-parse --short HEAD 2>/dev/null || echo unknown)

echo "=== [1/2] Reference bundles (pi@$REV) ==="
python3 scripts/build-references.py "$PI_REPO"
echo ""

echo "=== [2/2] Changelog ==="
python3 scripts/build-changelog.py "$PI_REPO" "$REV"
echo ""

echo "Done. Review git diff, then commit on a feature branch:"
echo "  git checkout -b refresh-\$(date +%Y-%m-%d)"
echo "  git add references/ && git commit -m 'Refresh references (pi@$REV)'"
