#!/usr/bin/env bash
# Build a Vimmite V6 installer ISO from the published GHCR image.
#
# This is the BlueBuild generate-iso "image" path, calling JasonN3's
# build-container-installer directly. BlueBuild 0.9.37 wraps that same
# container with sudo_cmd, which re-prompts from a child process and is
# what made the old wrapper fail. Privilege elevation happens once here.

set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
PROJECT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
readonly PROJECT_DIR

MODE="published"
OUTPUT_DIR="${PROJECT_DIR}/iso"
WORK_DIR="${PROJECT_DIR}/.bluebuild-iso-work"
IMAGE="ghcr.io/linuxmunchies/vimmite-v6-kinoite:latest"
RECIPE="${PROJECT_DIR}/recipes/vimmite.yml"
ISO_NAME="vimmite-v6-kinoite.iso"
OS_VERSION=""
OFFLINE=0
DRY_RUN=0
FORCE=1

# Same installer tag BlueBuild 0.9.37 uses. Digest pins the known-good image.
readonly INSTALLER_IMAGE="ghcr.io/jasonn3/build-container-installer:v1.4.0@sha256:a6b52ef0b410a625d7abd16f0467d257ef8db1ec94f672a89d5b95cb25487de1"
readonly SECURE_BOOT_KEY_URL="https://github.com/ublue-os/bazzite/raw/main/secure_boot.der"
readonly ENROLLMENT_PASSWORD="universalblue"
readonly ARCHIVE_NAME="vimmite-v6-kinoite.tar.gz"
readonly DNF_CACHE_VOLUME="vimmite-iso-dnf-cache"

SUDO_KEEPALIVE_PID=""
INVOKING_UID=""
INVOKING_GID=""

usage() {
    cat <<'EOF'
Build a Vimmite V6 installer ISO from the published container image.

Usage:
  scripts/build-iso.sh [published|local] [options]

Modes:
  published   Assemble from ghcr.io/linuxmunchies/vimmite-v6-kinoite (default).
              This is BlueBuild's generate-iso image path: a netinstall ISO
              that pulls the signed image during installation.
  local       Compose this checkout, then assemble an offline ISO from the
              resulting archive. Does not call bluebuild generate-iso recipe
              (blue-build/cli#661).

Options:
  --offline         Embed the published image so installation needs no registry.
  --output-dir DIR  ISO destination (default: ./iso).
  --work-dir DIR    Workspace for archives and caches (default: ./.bluebuild-iso-work).
  --image REF       Tagged source and installed-system update origin.
  --recipe FILE     Recipe used by local mode.
  --iso-name NAME   Output filename (default: vimmite-v6-kinoite.iso).
  --version N       Fedora installer version (default: read from the image).
  --no-force        Refuse to overwrite an existing ISO.
  --dry-run         Print the installer command and exit.
  -h, --help        Show this help.

ISO assembly needs rootful Podman for Lorax loop devices. The script asks for
sudo at most once, keeps that ticket alive, and never calls sudo from a child
the way `bluebuild generate-iso` does. Run it as your user, not via sudo.

A GitHub Actions workflow (Build installer ISO) produces the same netinstall
ISO without any local administrator password.
EOF
}

die() {
    printf 'error: %s\n' "$*" >&2
    exit 1
}

cleanup() {
    if [[ -n "$SUDO_KEEPALIVE_PID" ]]; then
        kill "$SUDO_KEEPALIVE_PID" 2>/dev/null || true
        wait "$SUDO_KEEPALIVE_PID" 2>/dev/null || true
    fi
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

if [[ $# -gt 0 && ( "$1" == "published" || "$1" == "local" ) ]]; then
    MODE="$1"
    shift
fi

while [[ $# -gt 0 ]]; do
    case "$1" in
        --offline)
            OFFLINE=1
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
        --version)
            [[ $# -ge 2 ]] || die "--version needs a value"
            OS_VERSION="$2"
            shift 2
            ;;
        --no-force)
            FORCE=0
            shift
            ;;
        --dry-run)
            DRY_RUN=1
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
if [[ "$MODE" == "local" ]]; then
    OFFLINE=1
fi

if [[ "$IMAGE" == *@* ]]; then
    die "--image must be a tagged reference (registry/name:tag), not a digest"
fi
if [[ "$IMAGE" != *:* ]]; then
    IMAGE="${IMAGE}:latest"
fi
if [[ "$IMAGE" =~ ^(.+)/([^/:]+):([^/:]+)$ ]]; then
    IMAGE_REPO="${BASH_REMATCH[1]}"
    IMAGE_NAME="${BASH_REMATCH[2]}"
    IMAGE_TAG="${BASH_REMATCH[3]}"
else
    die "--image must look like ghcr.io/linuxmunchies/vimmite-v6-kinoite:latest"
fi

command -v podman >/dev/null || die "Podman is not installed"
command -v skopeo >/dev/null || die "Skopeo is not installed"
if [[ "$MODE" == "local" ]]; then
    command -v bluebuild >/dev/null || die "BlueBuild is not installed"
fi

if [[ -n "${SUDO_UID:-}" ]]; then
    INVOKING_UID="$SUDO_UID"
    INVOKING_GID="${SUDO_GID:-$SUDO_UID}"
else
    INVOKING_UID="$(id -u)"
    INVOKING_GID="$(id -g)"
fi

mkdir -p -- "$OUTPUT_DIR" "$WORK_DIR"
OUTPUT_DIR="$(cd -- "$OUTPUT_DIR" && pwd)"
WORK_DIR="$(cd -- "$WORK_DIR" && pwd)"
readonly FINAL_ISO="${OUTPUT_DIR}/${ISO_NAME}"
readonly FINAL_CHECKSUM="${FINAL_ISO}-CHECKSUM"
readonly ARCHIVE_PATH="${WORK_DIR}/${ARCHIVE_NAME}"

if [[ -e "$FINAL_ISO" || -e "$FINAL_CHECKSUM" ]]; then
    if [[ "$FORCE" -eq 0 ]]; then
        die "output already exists: $FINAL_ISO (pass without --no-force to overwrite)"
    fi
    printf 'Overwriting existing ISO: %s\n' "$FINAL_ISO"
fi

required_gib=20
if [[ "$OFFLINE" -eq 1 ]]; then
    required_gib=40
fi
available_kib="$(df -Pk "$WORK_DIR" | awk 'NR == 2 {print $4}')"
[[ "$available_kib" -ge $((required_gib * 1024 * 1024)) ]] \
    || die "less than ${required_gib} GiB is free in $WORK_DIR"

resolve_os_version() {
    local version_label=""
    if [[ -n "$OS_VERSION" ]]; then
        [[ "$OS_VERSION" =~ ^[0-9]+$ ]] || die "--version must be a Fedora major version"
        return
    fi
    if [[ "$MODE" == "local" ]]; then
        version_label="$(awk '/^image-version:[[:space:]]*/ { print $2; exit }' "$RECIPE")"
        [[ "$version_label" =~ ^[0-9]+$ ]] || die "could not read image-version from $RECIPE"
        OS_VERSION="$version_label"
        return
    fi
    printf 'Reading Fedora version from %s...\n' "$IMAGE"
    version_label="$(skopeo inspect --retry-times 3 "docker://${IMAGE}" \
        --format '{{ index .Labels "org.opencontainers.image.version" }}')" \
        || die "could not inspect $IMAGE (run scripts/login-ghcr.sh if the package is private)"
    if [[ "$version_label" =~ ^([0-9]+) ]]; then
        OS_VERSION="${BASH_REMATCH[1]}"
    else
        die "image is missing a numeric org.opencontainers.image.version label"
    fi
}

keep_sudo_alive() {
    while sudo -n true 2>/dev/null; do
        sleep 50
    done
}

run_root() {
    if [[ ${EUID} -eq 0 ]]; then
        "$@"
    else
        sudo -n -- "$@"
    fi
}

setup_rootful_podman() {
    if [[ ${EUID} -eq 0 ]]; then
        printf 'Already root; using rootful Podman directly.\n'
        return
    fi
    command -v sudo >/dev/null || die "sudo is required for ISO assembly (Lorax needs loop devices)"
    if sudo -n true 2>/dev/null; then
        printf 'Using an existing sudo ticket for rootful Podman.\n'
    else
        if [[ ! -t 0 ]]; then
            die "ISO assembly needs one sudo login. Run from a terminal, or use the Build installer ISO GitHub Action."
        fi
        printf 'ISO assembly needs rootful Podman for Lorax. This is the only password prompt.\n'
        sudo -v || die "sudo authentication failed"
    fi
    keep_sudo_alive &
    SUDO_KEEPALIVE_PID=$!
}

stage_offline_archive() {
    if [[ "$MODE" == "local" ]]; then
        printf 'Building the Vimmite image into an OCI archive...\n'
        mkdir -p -- "${WORK_DIR}/bluebuild-temp"
        (
            cd -- "$PROJECT_DIR"
            bluebuild build --archive "$WORK_DIR" --tempdir "${WORK_DIR}/bluebuild-temp" "$RECIPE"
        )
    else
        printf 'Downloading %s into an OCI archive...\n' "$IMAGE"
        skopeo copy --retry-times 3 "docker://${IMAGE}" "oci-archive:${ARCHIVE_PATH}.partial"
        mv -f -- "${ARCHIVE_PATH}.partial" "$ARCHIVE_PATH"
    fi
    [[ -s "$ARCHIVE_PATH" ]] || die "image archive was not produced at $ARCHIVE_PATH"
    skopeo inspect "oci-archive:${ARCHIVE_PATH}" >/dev/null \
        || die "archive failed inspection: $ARCHIVE_PATH"
}

resolve_os_version
[[ "$OS_VERSION" =~ ^[0-9]+$ ]] || die "internal error: Fedora version is not numeric"

PODMAN_ARGS=(
    run --rm --privileged
    --security-opt label=disable
    --network=host
    --pull=missing
    --volume "${OUTPUT_DIR}:/build-container-installer/build"
    --volume "${DNF_CACHE_VOLUME}:/cache/dnf"
)
INSTALLER_ENV=(
    "VERSION=${OS_VERSION}"
    "VARIANT=Kinoite"
    "IMAGE_REPO=${IMAGE_REPO}"
    "IMAGE_NAME=${IMAGE_NAME}"
    "IMAGE_TAG=${IMAGE_TAG}"
    "IMAGE_SIGNED=true"
    "ISO_NAME=build/${ISO_NAME}"
    "DNF_CACHE=/cache/dnf"
    "SECURE_BOOT_KEY_URL=${SECURE_BOOT_KEY_URL}"
    "ENROLLMENT_PASSWORD=${ENROLLMENT_PASSWORD}"
    "WEB_UI=false"
)

if [[ "$OFFLINE" -eq 1 ]]; then
    PODMAN_ARGS+=(--volume "${WORK_DIR}:/img_src:ro")
    INSTALLER_ENV+=("IMAGE_SRC=oci-archive:/img_src/${ARCHIVE_NAME}")
fi

printf '\nVimmite V6 ISO build\n'
printf '  mode:     %s\n' "$MODE"
printf '  image:    %s\n' "$IMAGE"
printf '  fedora:   %s\n' "$OS_VERSION"
printf '  offline:  %s\n' "$([[ "$OFFLINE" -eq 1 ]] && printf 'yes' || printf 'no (netinstall)')"
printf '  output:   %s\n' "$FINAL_ISO"
printf '  engine:   %s\n\n' "$INSTALLER_IMAGE"

if [[ "$DRY_RUN" -eq 1 ]]; then
    printf 'Dry run; installer command:\n'
    printf '  podman'
    printf ' %q' "${PODMAN_ARGS[@]}" "$INSTALLER_IMAGE" "${INSTALLER_ENV[@]}"
    printf '\n'
    exit 0
fi

if [[ "$OFFLINE" -eq 1 ]]; then
    stage_offline_archive
fi

setup_rootful_podman

printf 'Pulling the installer image...\n'
run_root podman pull "$INSTALLER_IMAGE" >/dev/null

# Drop a previous ISO so a failed run cannot leave a stale success artifact.
run_root rm -f -- "$FINAL_ISO" "$FINAL_CHECKSUM"

printf 'Building %s...\n' "$ISO_NAME"
run_root podman "${PODMAN_ARGS[@]}" "$INSTALLER_IMAGE" "${INSTALLER_ENV[@]}"

[[ -s "$FINAL_ISO" ]] || die "installer completed without producing $FINAL_ISO"
if [[ ! -s "$FINAL_CHECKSUM" ]]; then
    printf 'Installer did not write a checksum; creating one.\n'
    (
        cd -- "$OUTPUT_DIR"
        sha256sum "$ISO_NAME" > "${ISO_NAME}-CHECKSUM"
    )
fi

run_root chown "${INVOKING_UID}:${INVOKING_GID}" -- "$FINAL_ISO" "$FINAL_CHECKSUM"
run_root chmod u+w,a+r -- "$FINAL_ISO" "$FINAL_CHECKSUM"

printf 'Verifying SHA-256 checksum...\n'
(
    cd -- "$OUTPUT_DIR"
    sha256sum -c "${ISO_NAME}-CHECKSUM"
)

if command -v checkisomd5 >/dev/null; then
    printf 'Verifying embedded installation-media checksum...\n'
    checkisomd5 "$FINAL_ISO"
fi

if command -v xorriso >/dev/null; then
    boot_report="$(xorriso -indev "$FINAL_ISO" -report_el_torito plain 2>&1)"
    grep -Eq 'El Torito boot img.*BIOS.*y' <<<"$boot_report" \
        || die "ISO BIOS boot catalog validation failed"
    grep -Eq 'El Torito boot img.*UEFI.*y' <<<"$boot_report" \
        || die "ISO UEFI boot catalog validation failed"
    printf 'BIOS and UEFI boot catalogs look valid.\n'
fi

printf '\nISO ready: %s\n' "$FINAL_ISO"
printf 'Checksum:  %s\n' "$FINAL_CHECKSUM"
if [[ "$OFFLINE" -eq 0 ]]; then
    printf 'This is a netinstall ISO. The target machine needs network access to pull\n'
    printf '%s during installation.\n' "$IMAGE"
    printf 'Pass --offline to embed the image for a self-contained installer.\n'
fi
printf 'After install, rpm-ostree status should show %s\n' "$IMAGE_REPO/$IMAGE_NAME"
