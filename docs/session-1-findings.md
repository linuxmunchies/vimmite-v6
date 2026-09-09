# Session 1 implementation findings (pre-V6 image)

Date: 2026-08-26

This record separates repository declarations, observations from the disposable
fresh-install host, the implemented correction, and validation that still
requires booting the newly composed image.

## Fresh-host baseline

The test machine was running the signed pre-V6
`ghcr.io/linuxmunchies/vimmite3-kinoite:latest` deployment with Fedora Kinoite
44 and kernel `7.1.10-200.fc44.x86_64`. It was not an older Vimmite deployment.

### First-boot network failure

The first offline boot started `system-flatpak-setup.service` at 17:49:59. The
service failed once per minute through 17:56:01 with:

```text
Can't load uri https://dl.flathub.org/repo/flathub.flatpakrepo ...
[6] Could not resolve hostname
```

The image's drop-in allowed only six restarts within 15 minutes. After that
limit was exhausted, connecting Wi-Fi could not start another attempt; the next
boot retriggered the one-shot timer and installed all 26 declared Flatpaks.

The correction disables the start-rate limit for both BlueBuild Flatpak setup
services and retries failed work every two minutes. A successful reconciliation
still exits normally, so this does not create a periodic installer after setup
has converged. Journal entries and the service's failed state retain diagnostic
visibility while offline.

The user-scoped service also touches its remote and can require the network, so
it receives the same policy. Other existing Vimmite user setup observed during
this audit was local. BlueBuild's Brew module stages Homebrew in the image and
copies it into its runtime location through `brew-setup`, so initial Brew setup
does not clone Homebrew on the first boot.

### Shell and home workspace

The account database showed `/bin/bash`, `/etc/default/useradd` selected Bash,
and the home contained Fedora's stock `.zshrc` but no `.zim`, `.zimrc`, or Zim
initialization. The old design only offered an opt-in `ujust` command, and that
command cloned modules from the network.

Zim itself was already checksum-pinned in the image. The correction also pins
every configured Zim module by commit, resolves the complete module tree during
image composition, seeds it through `/etc/skel`, and changes the account-tool
default to `/usr/bin/zsh`. The generated initializer is deliberately rebuilt in
each home so it does not retain the build-time path. The `ujust setup-zsh`
command remains an idempotent repair path for upgraded accounts.

The directory tmpfiles declaration was installed in
`/usr/lib/user-tmpfiles.d`, but Fedora 44's user tmpfiles manager searches
`/usr/share/user-tmpfiles.d`. Running the declaration explicitly created all
three directories immediately, confirming that the entries themselves were
valid. The image now places the file in the searched vendor directory.

### Virtualization

The fresh host had `/dev/kvm`, `kvm_amd`, QEMU 10.2.2, libvirt 12.0.0, OVMF,
software TPM support, all declared modular sockets, an active/autostart default
NAT network, and the Arch Linux ISO in `~/Downloads`. Root could connect to
`qemu:///system`; the normal user received a polkit authentication denial.

Fedora's stock rule only authorizes members of `libvirt`, while the installer
created the administrator in `wheel`. Vimmite now authorizes administrators in
`wheel` for `org.libvirt.unix.manage`. This preserves polkit mediation for
non-administrators, works for desktop and SSH sessions, and avoids a
post-install group mutation and logout.

The first diskless Arch ISO launch then exposed an Atomic-host packaging gap:
`swtpm-tools` owns `/var/lib/swtpm-localca`, but the mutable directory was not
materialized in the deployed `/var`. `swtpm_setup` runs its CA helper as `tss`,
so it could not create the root-owned directory. An image tmpfiles rule now
creates it as `tss:root` mode `0750`, matching the RPM metadata.

The next launch reached QEMU but could not traverse the installer's mode-0700
home directory to open the ISO under `~/Downloads`. `setup-virtualization` now
adds only a `qemu:--x` ACL to the invoking user's home. That permits path
traversal without allowing the service account to list the home directory.

After staging both fixes, the normal user launched the supplied Arch Linux ISO
in a transient, diskless VM. The guest ran with KVM/Q35, two vCPUs, Secure-Boot
OVMF, a TPM 2.0 emulator, virtio networking on the active default NAT network,
and SELinux enforcing. The transient domain was destroyed after inspection and
left no VM or disk behind.

### Multimedia

No codec package additions were justified. The selected Universal Blue base
already shipped the enabled `fedora-multimedia` repository and full
Negativo17 `ffmpeg`/`ffmpeg-libs`, plus GStreamer libav, `libheif`, `libavif`,
`libjxl`, and `libwebp`. The host successfully encoded and decoded short H.264,
HEVC, and AAC samples; FFmpeg also reported decoders for MP3, AV1, and VP9.
Adding RPM Fusion codec swaps on top of this base would duplicate and conflict
with the codec stack rather than fill a demonstrated gap.

### Added host and application components

- LACT is installed from `ilyaz/LACT` through BlueBuild's `dnf` COPR support.
  Current Fedora 44 repository metadata provides `lact` and `lact-headless`;
  the full `lact` package includes `/usr/bin/lact`, the desktop entry, and
  `lactd.service`. Vimmite installs the full package and enables `lactd.service`.
- Fedora 44 provides `input-remapper` 2.2.1 and
  `input-remapper.service`. Both package and service are declared in the image.
- BlueBuild's native `brew` module supplies the Homebrew runtime setup and
  update/upgrade timers. Analytics are disabled and the module's nofile limit
  support is enabled.
- Bitwarden, Warehouse, and LocalSend use Flathub IDs
  `com.bitwarden.desktop`, `io.github.flattool.Warehouse`, and
  `org.localsend.localsend_app`.
- IVPN is installed through the official repository URL using BlueBuild's
  native `dnf.repos.files` support. The current upstream Fedora instructions
  explicitly require `iptables-legacy` on Fedora 42+, and `ivpn-ui` depends on
  the daemon/CLI `ivpn` package. The image declares both `iptables-legacy` and
  `ivpn-ui`, then enables the exact packaged `ivpn-service.service` unit.
- The HyperX path/service and volume helper remain image-baked but inactive.
  `ujust hyperx-mic [status|enable|disable]` makes the hardware-specific watcher
  an explicit, reversible per-user choice.

The old deployment's global user-unit symlink was removed on the disposable
host. Enabling at user scope made the path unit enabled and active; disabling
it removed the per-user symlink and returned both states to disabled/inactive.
The host was left in that opt-out state.

### Final composed-image checks

The final unsigned local image built successfully as
`sha256:9b5495387c1aa8cb0e3a866838ae0d5b814f2dbaf0cddb2fadf40641bfeb2dd5`.
Artifact inspection confirmed LACT 0.10.0, input-remapper 2.2.1, IVPN 3.15.13,
the Fedora 44 virtualization stack, all enabled system services, and a disabled
HyperX user path by default. BlueBuild generated its automatic Atomic `/opt`
tmpfiles relocation for IVPN; after applying that rule in an ephemeral
container, the IVPN CLI reported version 3.15.13 with networking disabled.

The Brew runtime setup was exercised in an ephemeral no-network container and
`brew --version` reported Homebrew 6.0.19. A new-account simulation selected
`/usr/bin/zsh`, created `dev`, `sync`, and `ai`, and initialized all 14 Zim
modules with networking disabled. `dnf check`, recipe validation, Flatpak ID
validation, unit verification, shell syntax checks, justfile formatting, and
repository whitespace checks passed.

## Session 2 packaging candidates

Do not migrate these automatically. Review ownership, update cadence,
completions, and whether each command is required before Homebrew setup is
available.

Good first candidates for comparison are `bat`, `fd`, `lsd`, `tldr`, `ncdu`,
`yt-dlp`, and possibly `neovim`. Keep system-integrated foundations such as
Zsh, Git, Podman/Distrobox, libvirt/QEMU, hardware daemons, multimedia
libraries, and Steam in the image unless a later audit establishes a better
delivery mechanism. `podman-compose` needs a specific workflow check before it
is moved because it directly fronts the host Podman installation.

## Validation boundaries

Recipe validation, generated-recipe inspection, shell syntax, systemd/polkit
checks, and an unsigned local image build belong to this session. The following
remain physical acceptance items until the newly built deployment boots on the
test machine:

- offline boot, later Wi-Fi connection, and Flatpak completion without reboot;
- a genuinely new install-created account starting in Zsh with offline Zim;
- LACT and input-remapper GUI/device behavior;
- Homebrew boot-time setup, PATH integration, and command execution on a real
  deployed user session (the equivalent copied runtime passed in a container);
- IVPN service, account login, tunnel, DNS, and kill-switch behavior;
- the virt-manager GUI path itself (non-root CLI launch of the same Arch ISO
  passed with UEFI, KVM, TPM, and NAT after staging the image fixes); and
- suspend/resume with any running VM or hardware daemon.
