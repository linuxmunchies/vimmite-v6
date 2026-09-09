# Vimmite V6

<p align="center">
  <img src="docs/assets/vimmite-logo.svg" alt="Vimmite OS compass logo" width="144">
</p>

[![BlueBuild](https://github.com/linuxmunchies/vimmite-v6/actions/workflows/build.yml/badge.svg)](https://github.com/linuxmunchies/vimmite-v6/actions/workflows/build.yml)

> Vim's personal Fedora Atomic desktop: KDE, gaming, development, media, and
> workstation tools in one reproducible AMD/Intel image.

Vimmite V6 is **my OS**. It is the sixth generation of the image I use on my own
machines, rebuilt around Fedora Kinoite and BlueBuild so the configuration is
reviewable, repeatable, signed, and much easier to maintain than a pile of
post-install scripts.

It keeps the useful parts of my older Bazzite-based setup while deliberately
avoiding machine-specific hacks in the common image. Hardware-specific behavior
is either disabled by default or exposed as an explicit `ujust` profile.

## Project status

Vimmite V6 is in composition. Its prior generation completed a real fresh-install
acceptance pass on a Lenovo ThinkPad T16 Gen 1 with AMD graphics, exercising
boot, encryption, networking, audio, camera, Plasma, Flatpaks, Steam, Vulkan,
MangoHud, Distrobox, libvirt, and atomic updates. Those results are useful
baseline evidence, not V6 acceptance evidence.

Build V6 locally, complete its physical acceptance checklist, and only then
publish it. The release gate requires a passing run on at least one AMD portable
system, the Strix Halo system, and the Intel/Arc system, with known limitations
explicitly recorded. Controllers, the EPOMAKER keyboard, HyperX audio, real game
workloads, and suspend/resume remain physical tests.

The intended published image is
[`ghcr.io/linuxmunchies/vimmite-v6-kinoite:latest`](https://github.com/linuxmunchies/vimmite-v6/pkgs/container/vimmite-v6-kinoite):
the portable AMD/Intel Fedora Kinoite image used by Vimmite V6 systems.
The source repository is private. The GHCR image must be made public after its
first approved publication for the unauthenticated installer and update commands
below to work; otherwise each client needs separate OSTree registry credentials.

## What is in Vimmite V6?

### Desktop and base system

- Fedora 44 Kinoite and KDE Plasma on Universal Blue's standard Fedora kernel
- Vimmite Graphite visual identity over Breeze Dark, with electric-indigo and
  gold accents plus coordinated desktop, lock, and login artwork
- Firefox on the host and Brave from Flathub
- AMD and Intel graphics support; no NVIDIA-specific image content
- LUKS-capable Atomic installation, signed OCI updates, and rollback deployments
- Wi-Fi, Bluetooth, PipeWire, camera, touchpad, and common laptop support
- Vim's standard home workspace created automatically as `~/sync`, `~/dev`,
  and `~/ai`

### Gaming

- Native Steam and `steam-devices`
- 64-bit and 32-bit MangoHud
- GameMode when pulled as Steam's normal weak dependency; Vimmite V6 adds no
  GameMode launch options or global performance tuning
- ProtonPlus and Bottles
- Mesa's 32-bit Vulkan drivers for Proton
- Controller rules and upstream PlayStation/Bluetooth kernel support
- Pinned and checksum-verified `lsfg-vk` for Lossless Scaling frame generation

Gamescope, Lutris, and Heroic are not preinstalled. Bazaar can install optional
applications later without expanding the base image.

### Workstation and development tools

- DNF: Git, Vim, Neovim, Zsh, Zim, Kitty, Fastfetch, Inxi, rsync,
  Smartmontools, NVMe CLI, lm_sensors, Rclone, tmux, tree, lsd, btop, Restic,
  and Nerd Fonts
- Homebrew: Bat, ncdu, fd, tealdeer (`tldr`), jq, dust, procs, yt-dlp,
  bbrew, zoxide, and Hugging Face's `hf` CLI
- Podman, Distrobox, and Podman Compose
- Declarative `vimmite-dev` toolbox with compilers, debuggers, Python/uv,
  Node/npm, Rust/Cargo, GitHub CLI, ripgrep, fzf, and host editor/agent bridges
- Zed from Flathub
- QEMU/KVM, modular libvirt daemons, UEFI firmware, software TPM support, and
  the virt-manager Flatpak
- Homebrew/Linuxbrew through BlueBuild's native Brew module
- LACT and input-remapper with their host services enabled
- IVPN UI, daemon, and Fedora 42+ legacy iptables backend
- Opt-in labeled-drive automounting for workstation/game drives

### Media and applications

- VLC, mpv, MediaInfo, Mixxx, FLAC tools, and yt-dlp
- OBS Studio, Kdenlive, Blender, GIMP, Krita, Gwenview, and SongRec
- Bitwarden, Warehouse, LocalSend, OnlyOffice, Obsidian, Signal, Telegram,
  Equibop, Feishin, RustDesk, SyncThingy, Flatseal, Resources, Coppwr, Gear
  Lever, and Bazaar

The required application set is installed system-wide from Flathub. A quiet
user-scoped Flathub remote is also created for optional apps.

## Hardware profiles and deliberate defaults

The common image is portable. It does not guess which computer it is running
on or enable special hardware services everywhere.

- **Ryzen AI MAX:** the legacy large-memory/IOMMU profile only applies after a
  strict CPU and DMI identity check.
- **Internal data drives:** labeled-drive automounting is opt-in.
- **Remote access:** SSH and Wake-on-LAN are opt-in.
- **Streaming:** Moonlight and Sunshine are optional per-user installs.
- **EPOMAKER EA75:** `hid_apple fnmode=2` is built into the image and initramfs.
- **HyperX Cloud Alpha Wireless:** microphone-volume handling is opt-in through
  `ujust hyperx-mic enable`.

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
build creates the package above; generate the installer locally from that
package with the following command.

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

To use the published image instead of composing the checkout, authenticate
while the GHCR package is private and select published mode:

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

While the GHCR package is private, the installed system also needs a
revocable personal access token (classic) scoped only to `read:packages`.
Store it in OSTree's root-only credential file before rebasing or updating:

```bash
read -rsp 'GHCR read token: ' GHCR_TOKEN; echo
printf '%s' "$GHCR_TOKEN" | sudo skopeo login \
  --authfile /etc/ostree/auth.json \
  --username linuxmunchies --password-stdin ghcr.io
unset GHCR_TOKEN
sudo chmod 600 /etc/ostree/auth.json
```

Use a dedicated token rather than a broad GitHub CLI credential. Remove the
file with `sudo rm /etc/ostree/auth.json` to revoke local access after revoking
the token on GitHub. This setup is unnecessary if the package is made public;
the repository itself can remain private.

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

## First boot

Required system Flatpaks reconcile automatically. Failed network-dependent
reconciliation retries every two minutes without exhausting a boot-time rate
limit, so connecting Wi-Fi is sufficient and no reboot is required.

New users start in Zsh with the image-baked Zim module tree and receive
`~/sync`, `~/dev`, and `~/ai` automatically. Homebrew is installed at runtime by
BlueBuild's `brew-setup` service and becomes available in interactive shells.
Plasma starts with the Vimmite Graphite global theme and desktop wallpaper;
the lock screen and SDDM login use the coordinated lock artwork. Kitty and
Fastfetch inherit the matching terminal profile. All appearance settings remain
user-selectable in System Settings.

Start with the guided first-run menu, then use Doctor to verify the result:

```bash
ujust vimmite-setup
ujust vimmite-doctor
```

The setup menu covers appearance, a Fedora development container, gaming and
streaming, local-AI backends and model storage, virtualization, SSH/Wake-on-LAN,
drive automounting, and the HyperX microphone helper. It shows the current
state and reversal path before making optional changes. `ujust --choose` remains
available for browsing every low-level recipe.

If Doctor finds a problem, create a private diagnostic archive with `ujust
vimmite-support-bundle`. It collects deployment, hardware, failed-service, and
focused current/previous-boot evidence; redacts usernames, home paths, network
addresses, and common credential forms; and excludes home-directory contents,
browser state, environment variables, and the full journal. Always review the
archive before sharing it.

Common setup commands:

| Goal | Command | Notes |
| --- | --- | --- |
| Guided first-run setup | `ujust vimmite-setup` | Reports state and undo guidance for every area |
| Check system health | `ujust vimmite-doctor` | Uses green, warning, and failure results |
| Create support evidence | `ujust vimmite-support-bundle` | Writes a mode-0600 redacted `.tar.gz` |
| Create the development box | `ujust vimmite-dev create` | Reproducible Fedora toolbox; project versions stay project-owned |
| Verify the development box | `ujust vimmite-dev doctor` | Compiles C/Rust and checks Python, JavaScript, editors, Git, and SSH agent |
| Restore the image-baked Zim setup | `ujust setup-zsh` | Preserves existing `.zshrc` and `.zimrc` |
| Use Zsh on an upgraded account | `ujust setup-zsh true` | Log out and back in afterward |
| Prepare virtualization | `ujust setup-virtualization` | Enables the default NAT network |
| Check drive automounting | `ujust automount status` | Safe on every machine |
| Enable labeled drives | `ujust automount enable` | Intended for explicitly opted-in workstation hosts |
| Install streaming | `ujust install-streaming moonlight` | Also accepts `sunshine` or `both` |
| Enable SSH | `ujust ssh-server enable` | Also opens the firewalld service |
| Inspect Wake-on-LAN | `ujust wake-on-lan` | Lists candidate wired interfaces |
| Inspect AI MAX profile | `ujust setup-ai-max status` | Refuses unsupported hardware |
| Install RamaLama only | `ujust ramalama-setup` | User-local CLI; does not download models |
| Install RamaLama and all models | `ujust ramalama-setup-all` | Requires at least 145 GiB free in the model store |
| Manage Strix Halo local AI | `ujust strix-halo-ai` | Stable Vulkan/ROCm Distroboxes for gfx1151 only |

See [the post-install profile guide](docs/post-install.md) for the full behavior
and reversal instructions.

## Lossless Scaling

The Vulkan layer is installed, but frame generation requires the purchased
Windows Lossless Scaling application in the native Steam library. Launch
`lsfg-vk-ui` to point the layer at `Lossless.dll` and create per-game profiles.

The upstream default configuration contains a `vkcube` profile. Before the DLL
exists, bypass LSFG when testing the baseline Vulkan stack:

```bash
DISABLE_LSFG=1 vkcube
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
encrypted Restic repositories for user-data backup, with a restore drill before
release. Model downloads and game installations are excluded by default;
irreplaceable model work and non-cloud saves must be included explicitly. See
[the personal-data backup policy](docs/personal-data-backup.md).

## Build and test locally

### Validate the recipe

```bash
bluebuild validate recipes/vimmite.yml
```

Preview the fully expanded recipe or generated Containerfile when debugging
module ordering:

```bash
bluebuild generate --display-full-recipe recipes/vimmite.yml
bluebuild generate recipes/vimmite.yml --output Containerfile
```

### Build without publishing

```bash
bluebuild build --no-sign recipes/vimmite.yml
```

The local build uses the checkout's modules and scripts, verifies pinned
downloads, pre-populates Zim, rebuilds initramfs, and produces a local OCI
image. Use `bluebuild build --help` to select a different build driver,
platform, archive, or temporary directory.

Run the physical acceptance checklist before treating a successful container
build as a release:

```bash
less docs/test-checklist.md
```

## CI, publication, and signing

[`.github/workflows/build.yml`](.github/workflows/build.yml) builds proposed
changes for pull requests without promoting them. Publishing is manual and the
workflow requires an explicit confirmation that the V6 physical acceptance
matrix and current-image build gate passed.

The private Cosign key is stored only in the GitHub Actions secret
`SIGNING_SECRET`. Never commit it. Only [`cosign.pub`](cosign.pub) belongs in
the repository.

Verify the published primary image:

```bash
cosign verify \
  --key cosign.pub \
  ghcr.io/linuxmunchies/vimmite-v6-kinoite:latest
```

Useful workflow commands for maintainers:

```bash
gh workflow run build.yml --repo linuxmunchies/vimmite-v6 -f release_approved=true
gh run list --repo linuxmunchies/vimmite-v6 --workflow build.yml --limit 10
gh run watch --repo linuxmunchies/vimmite-v6 <run-id> --exit-status
```

## Repository map

```text
recipes/vimmite.yml              Primary Kinoite recipe
recipes/modules/                 Hardware, packages, gaming, virtualization,
                                 configuration, and Flatpak modules
files/scripts/                   Pinned artifact and shell installers
files/vimmite/                   Files copied into the primary image
files/justfiles/vimmite.just     Vimmite V6 ujust commands
docs/post-install.md             Optional profile instructions
docs/development.md              Declarative development-box workflow
docs/branding.md                 Visual identity, palette, and asset map
docs/strix-halo-ai.md            Strix Halo llama.cpp setup and troubleshooting
docs/strix-halo-ai-configuration.md  Strix Halo server and model configuration
docs/personal-data-backup.md     Restic scope, exclusions, and restore gate
docs/test-checklist.md           Physical acceptance checklist
docs/architecture-proposal.md    Design and dependency rationale
docs/investigation.md            Original live-system audit
docs/vimmite-migration.md        Vimmite migration inventory
cosign.pub                       Public image-verification key
```

## Design rules

Vimmite V6 favors:

- declarative image composition over mutable post-install scripts;
- standard Fedora/Universal Blue mechanisms over one-off workarounds;
- pinned and checksum-verified external artifacts;
- system-wide defaults plus explicit, reversible machine profiles;
- signed publication and rollback-safe upgrades; and
- preserving Vim's workflow without pretending every machine is identical.

That is the point of Vimmite V6: **my desktop, my defaults, reproducibly built.**

## Documentation

- [Investigation and decisions](docs/investigation.md)
- [Architecture and dependency rationale](docs/architecture-proposal.md)
- [Vimmite migration inventory](docs/vimmite-migration.md)
- [Post-install profiles](docs/post-install.md)
- [Visual identity and brand assets](docs/branding.md)
- [Personal-data backup policy](docs/personal-data-backup.md)
- [Physical acceptance checklist](docs/test-checklist.md)
- [Session 1 implementation findings](docs/session-1-findings.md)
- [BlueBuild documentation](https://blue-build.org/)

## License

See [LICENSE](LICENSE).
