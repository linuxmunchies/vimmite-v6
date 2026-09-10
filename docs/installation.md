# Installation and updates

Run repository scripts from the repository root. The build workflow publishes
container images automatically; ISO creation is a separate local operation.

## Install from an ISO

### Before you start

You need:

- an x86-64 AMD or Intel computer;
- a USB drive that can be erased;
- a backup of anything important on the target computer;
- enough local disk space for the image layers and generated ISO; and
- the BlueBuild CLI plus a working Podman/Docker/Buildah environment.

BlueBuild is already installed inside BlueBuild-built systems. On another
system, follow the [official CLI installation documentation](https://blue-build.org/how-to/local/).

BlueBuild publishes an OCI image, not a downloadable ISO. A successful `main`
build publishes `ghcr.io/linuxmunchies/vimmite-v6-kinoite:latest`. Generate an
installer locally using one of the modes below.

The repository includes a wrapper that builds the current checkout by default,
stores the image as a persistent OCI archive, and assembles the ISO in a small
temporary KVM virtual machine:

```bash
scripts/build-iso.sh
```

The finished ISO and checksum are written to `iso/`. The VM provides the real
mount privileges Lorax needs without asking for the host administrator
password. It requires KVM/QEMU, `mkisofs`, SSH, curl, Skopeo, BlueBuild, Podman,
and at least 70 GiB of free workspace. Run `scripts/build-iso.sh --help` for
output, workspace, image, and recipe overrides.

The installer embeds the image archive for offline installation and records
the configured signed GHCR reference as the installed system's update origin
(the default is `ghcr.io/linuxmunchies/vimmite-v6-kinoite:latest`; override it
with `--image`). After installation, `rpm-ostree status` must show
`ghcr.io/linuxmunchies/vimmite-v6-kinoite`, not Fedora's base image.

If ISO assembly needs to be retried without rebuilding the image, reuse the
validated archive:

```bash
scripts/build-iso.sh --reuse-archive --iso-name vimmite-v6-kinoite-retry.iso
```

To use the published image instead of composing the checkout, select published
mode. The GHCR package is public, so this pull does not need registry login:

```bash
scripts/build-iso.sh published
```

If Skopeo reports unauthorized access, the package is private again (source
repository visibility does not control that). Then authenticate and retry:

```bash
scripts/login-ghcr.sh
scripts/build-iso.sh published
```

The login helper uses the active GitHub CLI account and passes its token to
Skopeo over standard input; it does not print or store the token in this
repository. If GitHub CLI reports an expired login, run `gh auth login
--hostname github.com`, then `gh auth refresh --hostname github.com --scopes
read:packages`, before retrying the helper.

Do not use `bluebuild generate-iso recipe` with BlueBuild 0.9.37 here. That
version can create the local archive and then mount an empty `/img_src` into
the installer, causing the late `archive file not found` failure tracked in
[blue-build/cli issue #661](https://github.com/blue-build/cli/issues/661). The
wrapper deliberately separates image composition from ISO assembly, validates
the archive on both sides of the VM boundary, and preserves it for fast retries.
It also verifies the SHA-256 checksum and Fedora embedded media checksum before
reporting success.

### Write and boot the installer

Use Fedora Media Writer or another trusted graphical image writer to write the
ISO to the USB drive. Double-check the selected device: writing an image erases
the target drive.

Boot the USB in UEFI mode, complete the Kinoite installer, configure disk
encryption and the initial user, then reboot into Vimmite V6. Keep the encryption
passphrase available for every cold boot.

## Rebase an existing Fedora Atomic installation

This is only for an existing Atomic Fedora desktop such as Kinoite or
Silverblue. Do not run these commands on traditional mutable Fedora.

Rebase and `rpm-ostree upgrade` pull the public GHCR package and do not need
`/etc/ostree/auth.json`. Source-repository visibility is independent of that;
keep the container package public if you want unattended updates without
credentials.

If an existing install still has `/etc/ostree/auth.json` from the
private-package period and you no longer need it:

```bash
sudo rm /etc/ostree/auth.json
```

Only if the GHCR package is private again, install a revocable personal access
token (classic) scoped only to `read:packages` in OSTree's root-only credential
file before rebasing or updating:

```bash
read -rsp 'GHCR read token: ' GHCR_TOKEN; echo
printf '%s' "$GHCR_TOKEN" | sudo skopeo login \
  --authfile /etc/ostree/auth.json \
  --username linuxmunchies --password-stdin ghcr.io
unset GHCR_TOKEN
sudo chmod 600 /etc/ostree/auth.json
```

Use a dedicated token rather than a broad GitHub CLI credential. Remove the
file with `sudo rm /etc/ostree/auth.json` after revoking the token on GitHub.

The first rebase uses the unverified transport once so the image can install
Vimmite V6's signing policy and public key:

```bash
sudo rpm-ostree rebase \
  ostree-unverified-registry:ghcr.io/linuxmunchies/vimmite-v6-kinoite:latest
sudo systemctl reboot
```

After booting Vimmite V6, move permanently to the signed transport:

```bash
sudo rpm-ostree rebase \
  ostree-image-signed:docker://ghcr.io/linuxmunchies/vimmite-v6-kinoite:latest
sudo systemctl reboot
```

Confirm the signed origin and keep the previous deployment available:

```bash
rpm-ostree status
```


## Updating and rolling back

Stage the latest signed image:

```bash
sudo rpm-ostree upgrade
rpm-ostree status
sudo systemctl reboot
```

Atomic updates retain the previous deployment. If a new deployment is bad,
select the previous entry from the boot menu or roll back from the running
system:

```bash
sudo rpm-ostree rollback
sudo systemctl reboot
```

Do not delete the previous deployment until the new image has passed boot,
network, graphics, audio, suspend/resume, and any machine-specific dock tests.

Deployment rollback does not protect personal files. Vimmite standardizes on
encrypted Restic repositories for user-data backup, with a restore drill before relying on the backup. Model downloads and game installations are excluded by default;
irreplaceable model work and non-cloud saves must be included explicitly. See
[the personal-data backup policy](personal-data-backup.md).
