#!/usr/bin/env bash

set -Eeuo pipefail

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

command -v gh >/dev/null || die "GitHub CLI (gh) is not installed"
command -v skopeo >/dev/null || die "Skopeo is not installed"

if ! gh auth status --hostname github.com >/dev/null 2>&1; then
  cat >&2 <<'EOF'
GitHub CLI is not authenticated. Sign in and grant package-read access first:

  gh auth login --hostname github.com
  gh auth refresh --hostname github.com --scopes read:packages

Then run this script again.
EOF
  exit 1
fi

username="$(gh api user --jq .login)"
[[ -n "$username" ]] || die "could not determine the authenticated GitHub username"

printf 'Logging Skopeo in to GHCR as %s...\n' "$username"
gh auth token --hostname github.com \
  | skopeo login ghcr.io --username "$username" --password-stdin

printf 'GHCR login complete. You can now run scripts/build-iso.sh published.\n'
