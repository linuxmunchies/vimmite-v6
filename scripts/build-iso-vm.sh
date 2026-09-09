#!/usr/bin/env bash

set -Eeuo pipefail

ARCHIVE_PATH=""
OUTPUT_DIR=""
WORK_DIR=""
ISO_NAME="vimmite-v6-kinoite.iso"
OS_VERSION="44"
VM_MEMORY_MB="16384"
VM_CPUS="8"
TARGET_IMAGE="ghcr.io/linuxmunchies/vimmite-v6-kinoite:latest"

readonly INSTALLER_IMAGE="ghcr.io/jasonn3/build-container-installer:v1.4.0@sha256:a6b52ef0b410a625d7abd16f0467d257ef8db1ec94f672a89d5b95cb25487de1"
readonly CLOUD_IMAGE_NAME="Fedora-Cloud-Base-Generic-44-1.7.x86_64.qcow2"
readonly CLOUD_IMAGE_URL="https://download.fedoraproject.org/pub/fedora/linux/releases/44/Cloud/x86_64/images/${CLOUD_IMAGE_NAME}"
readonly CLOUD_IMAGE_SHA256="28680fe5b371a5a82ebf43a31926e086a168e59949d03969c5093e7071f90b7f"

usage() {
  cat <<'EOF'
Assemble and verify an installer ISO from a persistent OCI archive in a local
KVM virtual machine. This avoids host sudo and blue-build/cli issue #661.

Usage:
  scripts/build-iso-vm.sh --archive FILE --work-dir DIR --output-dir DIR [options]

Options:
  --iso-name NAME    Output filename (default: vimmite-v6-kinoite.iso).
  --target-image REF Tagged installed system update image
                     (default: ghcr.io/linuxmunchies/vimmite-v6-kinoite:latest).
  --memory-mb MB     Builder VM memory (default: 16384).
  --cpus COUNT       Builder VM CPUs (default: 8).
  -h, --help         Show this help.
EOF
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --archive)
      [[ $# -ge 2 ]] || die "--archive needs a value"
      ARCHIVE_PATH="$2"
      shift 2
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
    --iso-name)
      [[ $# -ge 2 ]] || die "--iso-name needs a value"
      ISO_NAME="$2"
      shift 2
      ;;
    --target-image)
      [[ $# -ge 2 ]] || die "--target-image needs a value"
      TARGET_IMAGE="$2"
      shift 2
      ;;
    --memory-mb)
      [[ $# -ge 2 ]] || die "--memory-mb needs a value"
      VM_MEMORY_MB="$2"
      shift 2
      ;;
    --cpus)
      [[ $# -ge 2 ]] || die "--cpus needs a value"
      VM_CPUS="$2"
      shift 2
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

[[ -n "$ARCHIVE_PATH" ]] || die "--archive is required"
[[ -n "$OUTPUT_DIR" ]] || die "--output-dir is required"
[[ -n "$WORK_DIR" ]] || die "--work-dir is required"
[[ "$ISO_NAME" != */* ]] || die "--iso-name must be a filename, not a path"
[[ "$ISO_NAME" == *.iso ]] || ISO_NAME="${ISO_NAME}.iso"
[[ "$VM_MEMORY_MB" =~ ^[0-9]+$ ]] || die "--memory-mb must be numeric"
[[ "$VM_CPUS" =~ ^[0-9]+$ ]] || die "--cpus must be numeric"
if [[ "$TARGET_IMAGE" != *@* && "$TARGET_IMAGE" =~ ^(.+)/([^/:]+):([^/:]+)$ ]]; then
  readonly TARGET_IMAGE_REPO="${BASH_REMATCH[1]}"
  readonly TARGET_IMAGE_NAME="${BASH_REMATCH[2]}"
  readonly TARGET_IMAGE_TAG="${BASH_REMATCH[3]}"
else
  die "--target-image must be a tagged reference with registry, image name, and tag"
fi

for command_name in curl mkisofs qemu-img qemu-system-x86_64 realpath seq sha256sum ss ssh ssh-keygen timeout; do
  command -v "$command_name" >/dev/null || die "$command_name is not installed"
done
[[ -r /dev/kvm && -w /dev/kvm ]] || die "/dev/kvm is not accessible to this user"

mkdir -p -- "$OUTPUT_DIR" "$WORK_DIR"
OUTPUT_DIR="$(cd -- "$OUTPUT_DIR" && pwd)"
WORK_DIR="$(cd -- "$WORK_DIR" && pwd)"
ARCHIVE_PATH="$(realpath -- "$ARCHIVE_PATH")"
[[ -s "$ARCHIVE_PATH" ]] || die "archive not found or empty: $ARCHIVE_PATH"
[[ "$WORK_DIR" != *,* ]] || die "the work directory cannot contain a comma"

case "$ARCHIVE_PATH" in
  "${WORK_DIR}"/*) ;;
  *) die "the archive must be inside the work directory shared with the VM" ;;
esac
readonly ARCHIVE_RELATIVE="${ARCHIVE_PATH#"${WORK_DIR}/"}"
readonly FINAL_ISO="${OUTPUT_DIR}/${ISO_NAME}"
readonly FINAL_CHECKSUM="${FINAL_ISO}-CHECKSUM"
[[ ! -e "$FINAL_ISO" && ! -e "$FINAL_CHECKSUM" ]] || die "output already exists: $FINAL_ISO"

available_kib="$(df -Pk "$WORK_DIR" | awk 'NR == 2 {print $4}')"
[[ "$available_kib" -ge $((70 * 1024 * 1024)) ]] || die "less than 70 GiB is free in $WORK_DIR"

readonly CLOUD_IMAGE="${WORK_DIR}/${CLOUD_IMAGE_NAME}"
if ! printf '%s  %s\n' "$CLOUD_IMAGE_SHA256" "$CLOUD_IMAGE" | sha256sum -c --status 2>/dev/null; then
  printf 'Downloading the verified Fedora builder image...\n'
  curl -fL --retry 3 -o "${CLOUD_IMAGE}.download" "$CLOUD_IMAGE_URL"
  printf '%s  %s\n' "$CLOUD_IMAGE_SHA256" "${CLOUD_IMAGE}.download" | sha256sum -c --status \
    || die "Fedora cloud image checksum verification failed"
  mv -f -- "${CLOUD_IMAGE}.download" "$CLOUD_IMAGE"
fi

readonly VM_DIR="$(mktemp -d "${WORK_DIR}/vm.XXXXXX")"
readonly VM_OUTPUT_DIR="${VM_DIR}/output"
readonly VM_DISK="${VM_DIR}/builder.qcow2"
readonly VM_SEED="${VM_DIR}/seed.iso"
readonly VM_KEY="${VM_DIR}/id_ed25519"
readonly VM_PID_FILE="${VM_DIR}/qemu.pid"
readonly VM_CONSOLE="${VM_DIR}/console.log"
readonly VM_MONITOR="${VM_DIR}/monitor.sock"
mkdir -p -- "$VM_OUTPUT_DIR"

SSH_PORT=""
for candidate in $(seq 22222 22242); do
  if [[ -z "$(ss -ltnH "sport = :${candidate}" 2>/dev/null)" ]]; then
    SSH_PORT="$candidate"
    break
  fi
done
[[ -n "$SSH_PORT" ]] || die "no free local SSH port was found for the builder VM"

ssh-keygen -q -t ed25519 -N '' -f "$VM_KEY"
public_key="$(<"${VM_KEY}.pub")"
{
  printf '%s\n' '#cloud-config'
  printf '%s\n' 'users:'
  printf '%s\n' '  - name: builder'
  printf '%s\n' '    groups: [wheel]'
  printf '%s\n' '    shell: /bin/bash'
  printf '%s\n' '    sudo: ALL=(ALL) NOPASSWD:ALL'
  printf '%s\n' '    ssh_authorized_keys:'
  printf '      - %s\n' "$public_key"
  printf '%s\n' 'ssh_pwauth: false'
  printf '%s\n' 'disable_root: true'
  printf '%s\n' 'growpart:'
  printf '%s\n' '  mode: auto'
  printf '%s\n' "  devices: ['/']"
  printf '%s\n' 'resize_rootfs: true'
} >"${VM_DIR}/user-data"
{
  printf 'instance-id: vimmite-iso-%s\n' "$(basename "$VM_DIR")"
  printf '%s\n' 'local-hostname: vimmite-iso-builder'
} >"${VM_DIR}/meta-data"

mkisofs -quiet -output "$VM_SEED" -volid cidata -joliet -rock \
  "${VM_DIR}/user-data" "${VM_DIR}/meta-data"
qemu-img create -f qcow2 -F qcow2 -b "$CLOUD_IMAGE" "$VM_DISK" 100G >/dev/null

build_succeeded=0
cleanup() {
  local exit_status=$?
  local vm_pid=""
  if [[ -s "$VM_PID_FILE" ]]; then
    IFS= read -r vm_pid <"$VM_PID_FILE" || true
    if [[ "$vm_pid" =~ ^[0-9]+$ ]] && kill -0 "$vm_pid" 2>/dev/null; then
      timeout 10 ssh -i "$VM_KEY" -p "$SSH_PORT" \
        -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        -o ConnectTimeout=3 -o LogLevel=ERROR builder@127.0.0.1 \
        'sudo poweroff' >/dev/null 2>&1 || true
      for _ in $(seq 1 20); do
        kill -0 "$vm_pid" 2>/dev/null || break
        sleep 1
      done
      kill "$vm_pid" 2>/dev/null || true
    fi
  fi
  rm -f -- "$VM_KEY" "${VM_KEY}.pub" "${VM_DIR}/user-data" "${VM_DIR}/meta-data"
  if [[ "$build_succeeded" -eq 1 ]]; then
    rm -f -- "$VM_DISK" "$VM_SEED" "$VM_CONSOLE" "$VM_MONITOR" "$VM_PID_FILE" \
      "${VM_OUTPUT_DIR}/${ISO_NAME}" "${VM_OUTPUT_DIR}/${ISO_NAME}-CHECKSUM"
    rmdir -- "$VM_OUTPUT_DIR" 2>/dev/null || true
    rmdir -- "$VM_DIR" 2>/dev/null || true
  else
    printf 'Builder diagnostics preserved after failure: %s\n' "$VM_DIR" >&2
  fi
  return "$exit_status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

printf 'Starting the passwordless KVM ISO builder...\n'
qemu-system-x86_64 \
  -name vimmite-iso-builder \
  -machine accel=kvm \
  -cpu host \
  -smp "$VM_CPUS" \
  -m "$VM_MEMORY_MB" \
  -drive "file=${VM_DISK},if=virtio,format=qcow2" \
  -drive "file=${VM_SEED},if=virtio,format=raw,readonly=on" \
  -netdev "user,id=net0,hostfwd=tcp:127.0.0.1:${SSH_PORT}-:22" \
  -device virtio-net-pci,netdev=net0 \
  -virtfs "local,path=${WORK_DIR},mount_tag=hostshare,security_model=none,id=hostshare" \
  -display none \
  -serial "file:${VM_CONSOLE}" \
  -monitor "unix:${VM_MONITOR},server,nowait" \
  -pidfile "$VM_PID_FILE" \
  -daemonize

readonly SSH_DESTINATION="builder@127.0.0.1"
SSH_ARGS=(
  -i "$VM_KEY"
  -p "$SSH_PORT"
  -o StrictHostKeyChecking=no
  -o UserKnownHostsFile=/dev/null
  -o ConnectTimeout=5
  -o LogLevel=ERROR
)

vm_ready=0
for _ in $(seq 1 90); do
  if ssh "${SSH_ARGS[@]}" "$SSH_DESTINATION" true 2>/dev/null; then
    vm_ready=1
    break
  fi
  sleep 2
done
[[ "$vm_ready" -eq 1 ]] || die "builder VM did not become reachable; see $VM_CONSOLE"

ssh "${SSH_ARGS[@]}" "$SSH_DESTINATION" \
  'set -Eeuo pipefail; cloud-init status --wait || { status=$?; [[ $status -eq 2 ]]; }; sudo mkdir -p /mnt/host; sudo mount -t 9p -o trans=virtio,version=9p2000.L,msize=104857600 hostshare /mnt/host; sudo dnf install -y podman skopeo isomd5sum'

readonly REMOTE_ARCHIVE="/mnt/host/${ARCHIVE_RELATIVE}"
readonly CONTAINER_ARCHIVE="/img_src/${ARCHIVE_RELATIVE}"
readonly VM_RELATIVE="${VM_DIR#"${WORK_DIR}/"}"
readonly REMOTE_OUTPUT="/mnt/host/${VM_RELATIVE}/output"

printf -v quoted_remote_archive '%q' "oci-archive:${REMOTE_ARCHIVE}"
printf -v quoted_container_archive '%q' "oci-archive:${CONTAINER_ARCHIVE}"
printf -v quoted_output '%q' "${REMOTE_OUTPUT}:/build-container-installer/build"
printf -v quoted_iso '%q' "build/${ISO_NAME}"
printf -v quoted_version '%q' "$OS_VERSION"
printf -v quoted_image_repo '%q' "$TARGET_IMAGE_REPO"
printf -v quoted_image_name '%q' "$TARGET_IMAGE_NAME"
printf -v quoted_image_tag '%q' "$TARGET_IMAGE_TAG"

printf 'Validating the archive inside the builder VM...\n'
ssh "${SSH_ARGS[@]}" "$SSH_DESTINATION" \
  "sudo skopeo inspect ${quoted_remote_archive} >/dev/null"

printf 'Building %s...\n' "$ISO_NAME"
ssh "${SSH_ARGS[@]}" "$SSH_DESTINATION" \
  "sudo podman run --rm --privileged --network=host --security-opt label=disable \\
    --volume ${quoted_output} --volume /mnt/host:/img_src:ro \\
    --volume vimmite-iso-dnf-cache:/cache/dnf ${INSTALLER_IMAGE} \\
    VERSION=${quoted_version} IMAGE_SRC=${quoted_container_archive} VARIANT=Kinoite \\
    IMAGE_REPO=${quoted_image_repo} IMAGE_NAME=${quoted_image_name} \\
    IMAGE_TAG=${quoted_image_tag} IMAGE_SIGNED=true \\
    ISO_NAME=${quoted_iso} DNF_CACHE=/cache/dnf \\
    SECURE_BOOT_KEY_URL=https://github.com/ublue-os/bazzite/raw/main/secure_boot.der \\
    ENROLLMENT_PASSWORD=universalblue WEB_UI=false"

[[ -s "${VM_OUTPUT_DIR}/${ISO_NAME}" ]] || die "installer completed without producing the ISO"
[[ -s "${VM_OUTPUT_DIR}/${ISO_NAME}-CHECKSUM" ]] || die "installer did not produce a checksum"

printf -v quoted_remote_output '%q' "$REMOTE_OUTPUT"
printf -v quoted_iso_name '%q' "$ISO_NAME"
printf 'Verifying checksum and embedded media integrity...\n'
ssh "${SSH_ARGS[@]}" "$SSH_DESTINATION" \
  "cd ${quoted_remote_output} && sha256sum -c ${quoted_iso_name}-CHECKSUM && checkisomd5 ${quoted_iso_name}"

cp --reflink=auto -- "${VM_OUTPUT_DIR}/${ISO_NAME}" "$FINAL_ISO"
cp -- "${VM_OUTPUT_DIR}/${ISO_NAME}-CHECKSUM" "$FINAL_CHECKSUM"
(
  cd -- "$OUTPUT_DIR"
  sha256sum -c "${ISO_NAME}-CHECKSUM"
)

if command -v xorriso >/dev/null; then
  boot_report="$(xorriso -indev "$FINAL_ISO" -report_el_torito plain 2>&1)"
  grep -Eq 'El Torito boot img.*BIOS.*y' <<<"$boot_report" \
    || die "ISO BIOS boot catalog validation failed"
  grep -Eq 'El Torito boot img.*UEFI.*y' <<<"$boot_report" \
    || die "ISO UEFI boot catalog validation failed"
fi

printf '\nISO ready: %s\n' "$FINAL_ISO"
printf 'Checksum:  %s\n' "$FINAL_CHECKSUM"
build_succeeded=1
