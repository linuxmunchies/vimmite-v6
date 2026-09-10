#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
PROJECT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
readonly PROJECT_DIR

MODE="local"
OUTPUT_DIR="${PROJECT_DIR}/iso"
WORK_DIR="${PROJECT_DIR}/.bluebuild-iso-work"
IMAGE="ghcr.io/linuxmunchies/vimmite-v6-kinoite:latest"
RECIPE="${PROJECT_DIR}/recipes/vimmite.yml"
ARCHIVE_NAME="vimmite-v6-kinoite.tar.gz"
ISO_NAME="vimmite-v6-kinoite.iso"
REUSE_ARCHIVE=0
VERBOSE=0

usage() {
  cat <<'EOF'
Build a Vimmite V6 installer ISO without BlueBuild's broken generate-iso handoff.

Usage:
  scripts/build-iso.sh [local|published] [options]

Modes:
  local       Build the recipe in this checkout (default).
  published   Download the configured image from GHCR.

Options:
  --reuse-archive   Reuse the validated archive in the work directory.
  --output-dir DIR  ISO destination (default: ./iso).
  --work-dir DIR    Persistent build workspace (default: ./.bluebuild-iso-work).
  --image REF       Tagged published source and installed update origin.
  --recipe FILE     Recipe used by local mode.
  --iso-name NAME   Output filename.
  -v, --verbose     Enable verbose BlueBuild output.
  -h, --help        Show this help.

ISO assembly runs inside a temporary Fedora KVM builder and does not need the
host sudo password.
EOF
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

if [[ $# -gt 0 && ( "$1" == "local" || "$1" == "published" ) ]]; then
  MODE="$1"
  shift
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --reuse-archive)
      REUSE_ARCHIVE=1
      shift
      ;;
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

[[ "$ISO_NAME" != */* ]] || die "--iso-name must be a filename, not a path"
[[ "$ISO_NAME" == *.iso ]] || ISO_NAME="${ISO_NAME}.iso"
[[ "$MODE" != "local" || -f "$RECIPE" ]] || die "recipe not found: $RECIPE"

command -v skopeo >/dev/null || die "Skopeo is not installed"
if [[ "$MODE" == "local" && "$REUSE_ARCHIVE" -eq 0 ]]; then
  command -v bluebuild >/dev/null || die "BlueBuild is not installed"
  command -v podman >/dev/null || die "Podman is not installed"
fi

mkdir -p -- "$OUTPUT_DIR" "$WORK_DIR"
OUTPUT_DIR="$(cd -- "$OUTPUT_DIR" && pwd)"
WORK_DIR="$(cd -- "$WORK_DIR" && pwd)"
readonly ARCHIVE_PATH="${WORK_DIR}/${ARCHIVE_NAME}"

if [[ "$REUSE_ARCHIVE" -eq 1 ]]; then
  [[ -f "$ARCHIVE_PATH" ]] || die "archive not found: $ARCHIVE_PATH"
  printf 'Reusing persistent image archive: %s\n' "$ARCHIVE_PATH"
else
  archive_stage="$(mktemp -d "${WORK_DIR}/archive.XXXXXX")"
  staged_archive="${archive_stage}/${ARCHIVE_NAME}"

  if [[ "$MODE" == "local" ]]; then
    mkdir -p -- "${WORK_DIR}/bluebuild-temp"
    bluebuild_args=(build --archive "$archive_stage" --tempdir "${WORK_DIR}/bluebuild-temp")
    (( VERBOSE == 0 )) || bluebuild_args+=(--verbose)
    printf 'Building the Vimmite image into a persistent OCI archive...\n'
    (
      cd -- "$PROJECT_DIR"
      bluebuild "${bluebuild_args[@]}" "$RECIPE"
    )
  else
    printf 'Downloading %s into a persistent OCI archive...\n' "$IMAGE"
    skopeo copy --retry-times 3 "docker://${IMAGE}" "oci-archive:${staged_archive}"
  fi

  [[ -s "$staged_archive" ]] || die "image build did not produce $staged_archive"
  skopeo inspect "oci-archive:${staged_archive}" >/dev/null
  mv -f -- "$staged_archive" "$ARCHIVE_PATH"
  rmdir -- "$archive_stage" 2>/dev/null || true
fi

printf 'Validating image archive...\n'
skopeo inspect "oci-archive:${ARCHIVE_PATH}" >/dev/null

exec "${SCRIPT_DIR}/build-iso-vm.sh" \
  --archive "$ARCHIVE_PATH" \
  --target-image "$IMAGE" \
  --work-dir "$WORK_DIR" \
  --output-dir "$OUTPUT_DIR" \
  --iso-name "$ISO_NAME"
