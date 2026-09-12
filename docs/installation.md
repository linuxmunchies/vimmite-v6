# Installation and updates

Run repository scripts from the repository root. The image workflow publishes
container images automatically. ISO creation is a separate local command or
the **Build installer ISO** workflow.

## Install from an ISO

### Before you start

You need:

- an x86-64 AMD or Intel computer;
- a USB drive that can be erased;
- a backup of anything important on the target computer;
- Podman, Skopeo, and enough disk for the generated ISO (about 20 GiB for a
  netinstall, 40 GiB if you embed the image); and
- one sudo login so Lorax can use loop devices. Do not run the script as root.

Local-from-checkout builds also need the BlueBuild CLI. On a machine that is
not already running a BlueBuild image, follow the
[official CLI installation documentation](https://blue-build.org/how-to/local/).

BlueBuild publishes an OCI image, not a downloadable ISO. A successful `main`
build publishes `ghcr.io/linuxmunchies/vimmite-v6-kinoite:latest`. Generate an
installer from that image.

This follows BlueBuild's
[generate-iso from a remote image](https://blue-build.org/how-to/generate-iso/)
path. Under the hood that command runs
[JasonN3's build-container-installer](https://github.com/JasonN3/build-container-installer)
in a privileged container. Run the repository wrapper as your user; do not
prefix it with `sudo`:

```bash
scripts/build-iso.sh
```

Lorax needs loop devices, so the script asks for the administrator password
once, keeps that sudo ticket alive, and runs a single `podman run --privileged`
of the installer. It does not call `bluebuild generate-iso`, which re-invokes
sudo from a child process and is what produced the repeated sudo failures.

The finished ISO and checksum are written to `iso/`. The default is a
netinstall ISO: the target machine needs network access during installation to
pull `ghcr.io/linuxmunchies/vimmite-v6-kinoite:latest`. After installation,
`rpm-ostree status` must show that GHCR reference, not Fedora's base image.

To embed the image so installation can proceed offline:

```bash
scripts/build-iso.sh --offline
```

To compose this checkout instead of using the published image:

```bash
scripts/build-iso.sh local
```

Local mode still avoids `bluebuild generate-iso recipe`, which in BlueBuild
0.9.37 can mount an empty `/img_src` and fail with `archive file not found`
([blue-build/cli#661](https://github.com/blue-build/cli/issues/661)).

If Skopeo reports unauthorized access, the package is private again (source
repository visibility does not control that). Then authenticate and retry:

```bash
scripts/login-ghcr.sh
scripts/build-iso.sh
```

The login helper uses the active GitHub CLI account and passes its token to
Skopeo over standard input; it does not print or store the token in this
repository. If GitHub CLI reports an expired login, run `gh auth login
--hostname github.com`, then `gh auth refresh --hostname github.com --scopes
read:packages`, before retrying the helper.

You can also build the same netinstall ISO without a local administrator
password from the Actions tab: **Build installer ISO**. Download the artifact
when the run finishes.

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
