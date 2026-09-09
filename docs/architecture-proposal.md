# Vimmite V6 architecture proposal

Status: implemented as the sole Vimmite V6 recipe. The previous Bazzite recipe
has been retired after successful installation and update testing on hardware.

## Recommended foundation

Use `ghcr.io/ublue-os/kinoite-main:44` as the first non-Bazzite development
base.

This is a deliberate intermediate foundation, not a claim that Universal Blue
must remain underneath Vimmite V6 forever. It removes Bazzite's gaming policy and
custom OGC kernel while retaining a maintained KDE Atomic desktop, Fedora's
standard kernel, codecs, Flathub setup, Distrobox, `ujust`, device rules, image
update services, and the Universal Blue kernel-signing chain.

Pin the Fedora major release (`44`) during development instead of following the
floating `latest` tag. Major-version upgrades should be reviewed and tested as
pull requests. Routine rebuilds can still pick up refreshed Fedora 44 content.

### Why this is the least risky current option

- Universal Blue deliberately retained `kinoite-main` because Aurora and
  Bazzite consume it. That is stronger maintenance evidence than a base that is
  merely published but not widely exercised.
- The standard kernel reduces the OGC-specific suspend and portability surface.
- The base already solves the low-value but failure-prone desktop integration
  work: complete multimedia codecs, AMD and Intel graphics userspace,
  thumbnails, Flathub, Distrobox, update services, and common device rules.
- The selected `kinoite-main` output has no proprietary Nvidia driver stack.
  Vimmite V6 will not select an Nvidia image variant, install Nvidia packages, add
  an Nvidia repository, or ship Nvidia-specific configuration.

The generic Fedora kernel still contains upstream drivers for many hardware
families, including Nouveau. Stripping those individual modules would require a
custom kernel and would work against the portability and maintenance goals. We
can, however, remove the separately packaged `nvidia-gpu-firmware`, which is not
required on the AMD/Intel targets and currently costs about 106 MB.

### Foundation alternatives considered

| Foundation | Result | Reason |
| --- | --- | --- |
| `ghcr.io/ublue-os/kinoite-main:44` | Recommend | Actively consumed by Aurora/Bazzite, uses a standard Fedora kernel with the Universal Blue signing and akmod pipeline, and retains the desktop integration we actually need. |
| `ghcr.io/blue-build/base-images/fedora-kinoite:44` | Defer | Attractive in principle, but its maintainers are still publicly defining support scope and it introduces BlueBuild's separate kernel-signing key. It is built from the same experimental Fedora desktop OCI source, so it does not currently buy a more official foundation. |
| `quay.io/fedora-ostree-desktops/kinoite:44` | Do not use directly | This is an unofficial experimental desktop OCI source. Using it directly makes Vimmite V6 own codecs, image update behavior, kernel-module signing, and other integration without removing the underlying stability concern. |
| `quay.io/fedora/fedora-bootc:44` | Long-term candidate, not now | This is an official stable bootc base, but it contains no desktop. Building and maintaining KDE Atomic semantics from it would substantially increase R&D before any user-facing requirement is restored. |

Sources:

- [Universal Blue `main` repository](https://github.com/ublue-os/main)
- [Universal Blue rationale for retaining `kinoite-main`](https://github.com/ublue-os/main/issues/927)
- [BlueBuild base images](https://github.com/blue-build/base-images)
- [BlueBuild base-image support discussion](https://github.com/blue-build/base-images/issues/13)
- [BlueBuild image classification](https://github.com/blue-build/workshop/blob/main/src/data/images.ts)
- [BlueBuild akmods module](https://blue-build.org/reference/modules/akmods/)

## Shared image layers

The portable image should be composed in small declarative groups. These are
conceptual boundaries first; exact file names can be chosen during the rewrite.

### 1. Desktop and hardware baseline

- KDE Plasma from Kinoite.
- Firefox retained from the base.
- AMD and Intel Mesa/Vulkan/video acceleration supplied by the base.
- Standard Fedora/Universal Blue kernel; no Bazzite/OGC kernel.
- `steam-devices` for maintained controller access rules.
- Upstream `hid_playstation` for the primary DualShock-compatible receiver.
- Upstream Bluetooth HID support for Xbox controllers.
- No `xone` module because the Microsoft USB/RF adapter is not used.
- No global GPU-index or performance-policy tuning.
- Remove the standalone `nvidia-gpu-firmware` package after a build-time
  dependency check confirms it remains unneeded.

### 2. Gaming baseline

Recommended host packages:

- native Steam;
- `steam-devices`;
- `mangohud` (including the required 32-bit library path);
- AMD and Intel 64-bit and 32-bit Vulkan drivers already selected by the base.

Fedora 44 publishes MangoHud, Gamescope, and `steam-devices` directly.
Steam itself is nonfree. The selected `kinoite-main` base already enables its
Fedora Multimedia repository, which supplies the native Steam package and its
multilib dependencies. Vimmite V6 uses that inherited repository and adds no
gaming or Nvidia repository of its own.

Native Steam is the initial recommendation because it most closely matches the
working Bazzite arrangement and keeps host MangoHud, external game
drives, and Lossless Scaling integration straightforward. Flatpak Steam remains
a viable fallback, but it requires runtime-version-matched Vulkan extensions
and additional filesystem/environment overrides for Lossless Scaling.

Gamescope is deliberately excluded. Its integration and testing cost is not
justified by the current requirements, and it is not required to launch Steam
on Plasma.

Required Flatpaks in this layer:

- ProtonPlus;
- Bottles.

Lossless Scaling requires the purchased Windows application in the Steam
library and the `lsfg-vk` Vulkan layer. The development image installs upstream
`lsfg-vk` 1.0.0 from its exact release URL after verifying a pinned SHA-256
digest. It never follows an unpinned `latest` asset.

Sources:

- [Fedora `steam-devices`](https://packages.fedoraproject.org/pkgs/steam-devices/steam-devices/)
- [Fedora Gamescope](https://packages.fedoraproject.org/pkgs/gamescope/gamescope/)
- [Fedora MangoHud](https://packages.fedoraproject.org/pkgs/mangohud/mangohud/)
- [`lsfg-vk` installation guide](https://github.com/PancakeTAS/lsfg-vk/wiki/Installation-Guide)

### 3. Virtualization baseline

Keep the virt-manager Flatpak as the GUI; its current sandbox already has access
to `/run/libvirt` and the per-user libvirt runtime directory. Add an actual host
backend to the image:

- `qemu-kvm`;
- `libvirt-daemon-kvm`;
- `libvirt-daemon-config-network`;
- `libvirt-client`;
- `virt-install`;
- `edk2-ovmf`;
- `swtpm`.

Use Fedora/libvirt's modular socket-activated daemons rather than copying
Bazzite's one-shot legacy `libvirtd.service` workaround. Enable the required
QEMU, network, storage, secret, and node-device sockets declaratively. A
polkit rule authorizes administrators in `wheel`. A post-install
command starts the default NAT network if desired and runs a small
connection/VM-capability test.

Materialize `/var/lib/swtpm-localca` through tmpfiles with the ownership and
mode declared by the Fedora `swtpm-tools` RPM; immutable deployments do not
otherwise guarantee that package-owned mutable directory exists.

Sources:

- [libvirt modular daemons](https://libvirt.org/daemons.html)
- [`virtqemud` manual](https://www.libvirt.org/manpages/virtqemud.html)

### 4. Applications and developer environment

- Keep the current declared Flatpaks.
- Add Brave, ProtonPlus, Bazaar, virt-manager, Bitwarden, Warehouse, and
  LocalSend to the declared Flatpak set.
- Keep Lutris and Heroic out of the image; Bazaar can install them later.
- Keep Zed as a Flatpak.
- Keep Vim, Neovim, Git, Zsh, and the selected terminal utilities on the host.
- Keep Python, Go, and Rust toolchains in Distrobox rather than the host image.

Flatpaks should remain system-scoped so the required application set is
available to every user. The user-scoped Flathub remote can remain available for
optional applications. BlueBuild's current `default-flatpaks` module reconciles
the declared list at boot, so removals from that list must be intentional. The
system reconciliation service retries transient first-boot failures because the
network-online target can be reached before DNS is usable.

### 5. Shell design

Install Zsh in every image, resolve Zim modules at image-build time, seed new
accounts through `/etc/skel`, and make Zsh the account-tool default. The
idempotent `ujust setup-zsh` repair/upgrade path must not overwrite an existing
`.zshrc` without explicit confirmation.

Universal Blue removes `chsh` deliberately because rolling back to an image
without the selected shell can make login fail. Vimmite V6 should not silently
restore `chsh`. The post-install command can either configure Konsole to launch
Zsh (safest) or, after warning about the rollback constraint, use `usermod` to
make the image-baked `/usr/bin/zsh` the login shell. The latter is appropriate
only while every retained deployment includes Zsh.

### 6. Fonts and copied configuration

- Install Fira Code and JetBrains Mono Nerd Fonts from pinned artifacts with
  checksums. BlueBuild's convenience font module always fetches the latest
  release, so it is not the reproducible choice here.
- Keep the legacy Vesktop microphone identities as compatibility fallbacks and
  add Equibop's packaged executable identity. Acceptance still requires a real
  Equibop call to confirm the live PipeWire-Pulse properties and volume behavior.
- Offer an opt-in HyperX user-session rule/service that keeps the source at 90%
  and selects the device by stable properties rather than a transient PipeWire
  object ID.
- Retain `hid_apple fnmode=2` for the EPOMAKER EA75 and regenerate the image
  initramfs so the option applies even if the driver loads during early boot.
- Do not copy the old global low-latency PipeWire quantum until its benefit and
  suspend/power cost are measured.

## Post-install profiles

The common image should expose explicit, reversible `ujust` commands rather
than guessing hardware at image-build time.

| Profile | Intended behavior |
| --- | --- |
| `setup-zsh` | Install pinned Zim user state and select the requested shell behavior. |
| `setup-ai-max` | On the exact GMKtec AI MAX host only, opt into or undo the former large-memory values while removing `iommu=off`; clearly warn that `amdgpu.gttsize` is deprecated. |
| `automount` | Opt into Universal Blue's labeled internal Btrfs/ext4 drive automount service; disabled elsewhere. |
| `hyperx-mic` | Opt into the HyperX Cloud Alpha Wireless 90% microphone helper for the current user. |
| `setup-virtualization` | Prepare libvirt user access, default network, storage paths, and a backend test. |
| `install-streaming` | Install Moonlight, Sunshine, or both as user Flatpaks and run Sunshine's required host integration. |
| `ssh-server` | Enable or disable OpenSSH together with its firewalld service. |
| `wake-on-lan` | Configure magic-packet WOL on an explicitly selected NetworkManager Ethernet connection. |
| `vimmite-dev` | Build, assemble, verify, replace, and remove a reproducible rootless development toolbox while retaining the shared home. |

Machine-specific commands must print the changes they will make, be safe to
rerun, and provide a matching status or undo path where practical.

Development toolchains belong in the declarative `vimmite-dev` Containerfile,
not in the immutable host. Its assemble manifest provides rootless lifecycle
management and host bridges for the SSH agent, Git state, Zed, desktop opening,
and nested rootless Podman workflows. The container may carry a Fedora language
baseline, but each repository owns its actual Node, Python, Go, and Rust version
through mise, uv, native project metadata, or a devcontainer.

## Rollback and storage model

- Rely on bootc/rpm-ostree deployments for operating-system rollback. A failed
  update retains the previous deployment as a bootloader entry and can be made
  the default with `rpm-ostree rollback`.
- Keep the installer/default Btrfs layout unless testing identifies a concrete
  reason to customize it.
- Do not claim that an OS deployment rollback restores `/var` or home data; it
  does not. Use the separately documented encrypted Restic policy and restore
  gate for personal data.
- Do not port Vimmite's mutable-root Snapper setup into the image.

Source: [rpm-ostree administrator handbook](https://coreos.github.io/rpm-ostree/administrator-handbook/)

## Proposed acceptance gates before replacing the base

1. Build the proposed Fedora 44 image in CI with no Nvidia-specific packages or
   repositories and inspect its package manifest.
2. Boot a temporary deployment on the Ryzen AI MAX host without applying any
   shared kernel arguments.
3. Test native Steam, MangoHud, ProtonPlus, Bottles, the game drive,
   and the DualShock-compatible receiver before adding optional gaming pieces.
4. Test virt-manager against `qemu:///system`, a UEFI VM, a TPM-backed VM, NAT,
   shutdown, and resume.
5. Repeat a reduced hardware suite on the Ryzen 6550U/Radeon 660M and Intel
   Core Ultra/Arc systems.
6. Build and test the installer, including the reported post-install grey-screen
   case and the first reboot, before declaring the old installer replaced.
