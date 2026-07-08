#!/usr/bin/env bash

set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root_dir"

assert_contains() {
  local file="$1"
  local pattern="$2"

  if ! rg -q --fixed-strings "$pattern" "$file"; then
    echo "Missing expected text in $file: $pattern" >&2
    exit 1
  fi
}

assert_contains README.md '~/.codex/skills/agent-native-design'
assert_contains README.md '.codex/skills/agent-native-design'
assert_contains README_CN.md '~/.codex/skills/agent-native-design'
assert_contains README_CN.md '.codex/skills/agent-native-design'

assert_contains SKILL.md 'Includes sidecar metadata for OpenClaw, Hermes, pi-mono, and OpenAI Codex'
assert_contains README.md 'includes metadata for the platforms listed below'
assert_contains README_CN.md '并为下列平台提供元数据'

assert_contains SKILL.md 'Use the 14-criterion rubric to score the CLI.'
assert_contains SKILL.md 'Report the 14-criterion rubric score first'
assert_contains agents/openai.yaml 'Score a CLI on the 14-criterion rubric and summarize the seven design principles'

test -f LICENSE || {
  echo 'LICENSE file is missing' >&2
  exit 1
}

# Verify SKILL.md frontmatter version is not behind the latest reachable git tag.
# Catches the v1.0.1-style drift where a tag is cut without bumping the
# `version` field in the SKILL.md frontmatter metadata block.
verify_frontmatter_version_against_tag() {
  local fm_version
  fm_version=$(rg -oN '"version":"([0-9]+\.[0-9]+\.[0-9]+)"' SKILL.md -r '$1' | head -1 || true)
  if [ -z "$fm_version" ]; then
    echo 'SKILL.md frontmatter is missing a "version":"X.Y.Z" field' >&2
    exit 1
  fi

  local latest_tag
  latest_tag=$(git describe --tags --abbrev=0 2>/dev/null || true)
  if [ -z "$latest_tag" ]; then
    return 0  # no tags reachable; nothing to compare against (e.g. shallow clone)
  fi
  local tag_version="${latest_tag#v}"

  if [ "$fm_version" = "$tag_version" ]; then
    return 0
  fi

  # Semver compare via sort -V; the smaller version ends up first.
  local lower
  lower=$(printf '%s\n%s\n' "$fm_version" "$tag_version" | sort -V | head -1)
  if [ "$lower" = "$fm_version" ]; then
    echo "Frontmatter version $fm_version is behind latest git tag $latest_tag." >&2
    echo "Bump \"version\" in the SKILL.md frontmatter metadata to match (or exceed) the tag, then re-tag if needed." >&2
    exit 1
  fi
  # fm_version > tag_version is fine — that's the normal pre-release state.
}

verify_frontmatter_version_against_tag

echo 'Metadata validation passed.'
