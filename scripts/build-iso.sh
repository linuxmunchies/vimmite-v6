#!/usr/bin/env bash

set -Eeuo pipefail

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

MODE="published"
OUTPUT_DIR="${PROJECT_DIR}/iso"
WORK_DIR="${PROJECT_DIR}/.bluebuild-iso-work"
IMAGE="ghcr.io/linuxmunchies/vimmite-v6-kinoite:latest"
RECIPE="${PROJECT_DIR}/recipes/vimmite.yml"
ISO_NAME=""
VERBOSE=0

usage() {
  cat <<'EOF'
Build a Vimmite V6 installer ISO.

Usage:
  scripts/build-iso.sh [published|local] [options]

Modes:
  published  Generate from the published GHCR image (default and fastest).
  local      Build this checkout's recipe, then generate the ISO.

Options:
  --output-dir DIR  ISO destination (default: ./iso)
  --work-dir DIR    Temporary build files (default: ./.bluebuild-iso-work)
  --image REF       Published OCI image reference
  --recipe FILE     Recipe used by local mode
  --iso-name NAME   Output filename (a mode-specific name is the default)
  -v, --verbose     Enable verbose BlueBuild output
  -h, --help        Show this help

Examples:
  scripts/login-ghcr.sh
  scripts/build-iso.sh
  scripts/build-iso.sh local
  scripts/build-iso.sh published --iso-name Vimmite-V6.iso
EOF
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

if [[ $# -gt 0 && ( "$1" == "published" || "$1" == "local" ) ]]; then
  MODE="$1"
  shift
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir)
      [[ $# -ge 2 ]] || die "--output-dir needs a value"
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --work-dir)
      [[ $# -ge 2 ]] || die "--work-dir needs a value"
      WORK_DIR="$2"
      shift 2
      ;;
    --image)
      [[ $# -ge 2 ]] || die "--image needs a value"
      IMAGE="$2"
      shift 2
      ;;
    --recipe)
      [[ $# -ge 2 ]] || die "--recipe needs a value"
      RECIPE="$2"
      shift 2
      ;;
    --iso-name)
      [[ $# -ge 2 ]] || die "--iso-name needs a value"
      ISO_NAME="$2"
      shift 2
      ;;
    -v|--verbose)
      VERBOSE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown argument: $1"
      ;;
  esac
done

command -v bluebuild >/dev/null || die "BlueBuild is not installed"
command -v podman >/dev/null || die "Podman is not installed"
command -v sudo >/dev/null || die "sudo is required for final ISO assembly"
[[ "$MODE" != "local" || -f "$RECIPE" ]] || die "recipe not found: $RECIPE"

if [[ -z "$ISO_NAME" ]]; then
  if [[ "$MODE" == "local" ]]; then
    ISO_NAME="Vimmite-V6-local.iso"
  else
    ISO_NAME="Vimmite-V6.iso"
  fi
fi
[[ "$ISO_NAME" == *.iso ]] || ISO_NAME="${ISO_NAME}.iso"

mkdir -p -- "$OUTPUT_DIR" "$WORK_DIR"
OUTPUT_DIR="$(cd -- "$OUTPUT_DIR" && pwd)"
WORK_DIR="$(cd -- "$WORK_DIR" && pwd)"

if [[ -e "${OUTPUT_DIR}/${ISO_NAME}" ]]; then
  die "output already exists: ${OUTPUT_DIR}/${ISO_NAME}"
fi

available_kib=$(df -Pk "$WORK_DIR" | awk 'NR == 2 {print $4}')
if [[ "$available_kib" -lt $((80 * 1024 * 1024)) ]]; then
  die "less than 80 GiB is available in the build workspace: $WORK_DIR"
fi

BLUEBUILD_ARGS=()
(( VERBOSE == 0 )) || BLUEBUILD_ARGS+=(--verbose)
BLUEBUILD_ARGS+=(
  generate-iso
  --output-dir "$OUTPUT_DIR"
  --tempdir "$WORK_DIR"
  --iso-name "$ISO_NAME"
)

if [[ "$MODE" == "local" ]]; then
  BLUEBUILD_ARGS+=(recipe "$RECIPE")
else
  BLUEBUILD_ARGS+=(image "$IMAGE")
fi

printf 'Vimmite V6 ISO build\n'
printf '  mode:   %s\n' "$MODE"
printf '  source: %s\n' "$([[ "$MODE" == "local" ]] && printf '%s' "$RECIPE" || printf '%s' "$IMAGE")"
printf '  output: %s\n' "${OUTPUT_DIR}/${ISO_NAME}"
printf '  work:   %s\n\n' "$WORK_DIR"

# BlueBuild invokes sudo from a child process during installer assembly. That
# child cannot safely prompt for a password, so acquire a ticket here, where
# the user can see the prompt, and refresh it while a long local compose runs.
printf 'Authorizing final ISO assembly before the build starts...\n'
sudo -v || die "administrator authentication failed"

keep_sudo_ticket_alive() {
  while sleep 60; do
    sudo -n -v || return
  done
}

keep_sudo_ticket_alive &
SUDO_KEEPALIVE_PID=$!
cleanup_sudo_keepalive() {
  kill "$SUDO_KEEPALIVE_PID" 2>/dev/null || true
  wait "$SUDO_KEEPALIVE_PID" 2>/dev/null || true
}
trap cleanup_sudo_keepalive EXIT

if ! bluebuild "${BLUEBUILD_ARGS[@]}"; then
  if [[ "$MODE" == "published" ]]; then
    cat >&2 <<'EOF'

The published GHCR image may require authentication. Authenticate with:

  scripts/login-ghcr.sh

Or build entirely from this checkout without accessing the private image:

  scripts/build-iso.sh local
EOF
  fi
  exit 1
fi

printf '\nISO generation complete: %s\n' "${OUTPUT_DIR}/${ISO_NAME}"
