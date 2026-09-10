#!/usr/bin/env bash
set -euo pipefail

# File capabilities survive into the composed image. This must run after the
# dnf module that installs btop; a later RPM replacement would drop the cap.
readonly BTOP="/usr/bin/btop"

if [[ ! -x "${BTOP}" ]]; then
    echo "ERROR: btop is not installed at ${BTOP}." >&2
    exit 1
fi

if ! command -v setcap >/dev/null || ! command -v getcap >/dev/null; then
    echo "ERROR: setcap/getcap are unavailable; install libcap." >&2
    exit 1
fi

echo "Enabling CAP_PERFMON for ${BTOP}."
setcap cap_perfmon=ep "${BTOP}"

echo "Verifying capability:"
getcap "${BTOP}"

if ! getcap "${BTOP}" | grep -q 'cap_perfmon=ep'; then
    echo "ERROR: failed to set CAP_PERFMON on ${BTOP}." >&2
    exit 1
fi
