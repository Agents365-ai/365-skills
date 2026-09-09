#!/usr/bin/env bash
# Refresh doc references and changelog.
#
# Intended cadence: weekly (Sundays) — Pi releases ship every few days, but a
# weekly refresh keeps this reference skill current without churn.
#
# Usage: bash scripts/refresh.sh
set -euo pipefail
cd "$(dirname "$0")/.."

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

echo "=== [1/2] Fetch latest docs from pi repo ==="
FETCH_FLAGS=(--retry 3 --retry-delay 2 --connect-timeout 5 --max-time 20 --max-filesize 524288)
for f in index.md quickstart.md usage.md environment-variables.md providers.md llama-cpp.md security.md containerization.md settings.md keybindings.md sessions.md compaction.md extensions.md skills.md prompt-templates.md themes.md packages.md models.md custom-provider.md session-format.md sdk.md rpc.md json.md tui.md windows.md termux.md tmux.md terminal-setup.md shell-aliases.md development.md; do
	echo "  fetching $f..."
	curl -sfL "${FETCH_FLAGS[@]}" "https://raw.githubusercontent.com/earendil-works/pi/main/packages/coding-agent/docs/$f" -o "$TMPDIR/$f" || echo "  WARNING: $f failed"
done
python3 scripts/build-references.py "$TMPDIR"
echo ""

echo "=== [2/2] Changelog ==="
python3 scripts/fetch-changelog.py
echo ""

echo "Done. Review git diff, then commit on a feature branch:"
echo "  git checkout -b weekly-refresh-\$(date +%Y-%m-%d)"
echo "  git add references/"
echo "  git commit -m 'Weekly refresh: docs, changelog (\$(date +%Y-%m-%d))'"
echo "  git push -u origin HEAD && gh pr create --title 'Weekly refresh (\$(date +%Y-%m-%d))' --body 'Automated weekly refresh of docs and changelog.'"
