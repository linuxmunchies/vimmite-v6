# Vimmite migration inventory

This is a provisional classification of the active Vimmite scripts and its
archived monolith. It preserves their intent without treating the old installer
as a specification. Items that depend on the replacement base or current
upstream guidance remain open until those sources are verified.

## Source inventory

| Source | Intent |
| --- | --- |
| `main.sh` | Root-run orchestration, logging, cleanup, and progress |
| `01-system-base.sh` | RPM Fusion, codecs, Snapper, utilities, containers, and virtualization |
| `02-media-and-drivers.sh` | Multimedia packages, AMD/Intel acceleration, and fonts |
| `03-gaming.sh` | Steam stack, gaming tuning, and a fixed game-drive mount |
| `04-user-environment.sh` | Flatpaks, Brave, Zsh, fonts, keyboard, audio, and user directories |
| Archived previous-generation monolith | Earlier ROCm, Kickstart Neovim, application, and directory ideas |

The active scripts contain no explicit Proton installation, Gamescope,
emulation stack, controller driver, Distrobox setup, Wake-on-LAN setup, or SSH
setup. Much of the current gaming integration instead comes from Bazzite.

## Definitely migrate

These are confirmed requirements. Their old implementation is not approved.

- A complete gaming baseline: Steam, MangoHud, Vulkan support, Steam
  controller permissions, ProtonPlus, Bottles, and Lossless Scaling.
- Controller support for the Chicken Run DualShock 4-compatible receiver,
  Bluetooth Xbox controllers, and a future Steam Controller.
- A working host virtualization backend for virt-manager, including QEMU/KVM,
  libvirt networking, and appropriate socket activation.
- Distrobox as the preferred home for Python, Go, and Rust development stacks.
- Neovim on the host and Zed as a Flatpak.
- Zsh as the preferred interactive shell, using Zim rather than Vimmite's
  generated `zsh-kick` configuration.
- Firefox as a guaranteed browser and Brave delivered as a Flatpak.
- The declared Vimmite V6 GUI application set on every machine.
- Multimedia playback/creation and the codecs needed by the retained
  applications, implemented appropriately for the selected base.

## Probably useful

These appear useful but need pruning against the base image and actual use.

- Firmware and diagnostics: `fwupd`, `inxi`, `btop`/`htop`, `libva-utils`,
  and Intel GPU diagnostic tools.
- Storage/network tools: `cifs-utils`, `samba-client`, `exfatprogs`, `rsync`,
  `rclone`, `lsof`, `p7zip`, and `unzip`.
- Terminal utilities such as `fzf`, `fd-find`, `jq`, `bat`, `ncdu`, `tldr`,
  and a terminal multiplexer.
- Broad Noto, Liberation, and IBM Plex font coverage.
- Fira Code and JetBrains Mono Nerd Fonts, provided reproducibly rather than
  downloaded from an unpinned latest release at install time. These two families
  are confirmed as sufficient.
- The `hid_apple fnmode=2` setting required for correct EPOMAKER EA75 function
  key behavior, including it in the regenerated image initramfs.

## Already replaced by a better mechanism

- Flatpak installation shell commands become the BlueBuild
  `default-flatpaks` module.
- Host package installation becomes declarative image packages rather than a
  root script calling `dnf` repeatedly.
- Mutable `dnf upgrade`, package-cache cleanup, and live repository editing are
  replaced by rebuilding and deploying a signed image.
- Brave's third-party RPM repository is replaced by its Flatpak.
- Language compiler stacks move from the host into Distrobox.
- Vimmite's generated Zsh configuration is replaced by a deliberate Zim
  bootstrap/configuration design.
- Service enablement should use declarative image presets/modules rather than
  starting services during an image build.
- Manual initramfs rebuilding is owned by the image build and is only retained
  where copied configuration genuinely must be present during early boot.
- Device access should use maintained udev/logind policy rather than broad,
  hard-coded membership in `input`, `video`, or `render` groups.

## Obsolete, brittle, or inappropriate to port

- All Nvidia references, repository handling, diagnostics, and implied driver
  paths are out of scope.
- CPU detection using `lscpu` inside an image build cannot select runtime GPU
  support for a portable AMD/Intel image. Both supported hardware paths must be
  assembled intentionally.
- Hard-coding `gpu_device=0` and AMD performance policy globally is
  incompatible with Intel and multi-GPU portability.
- The installed `xone` out-of-tree kernel module is unnecessary for the
  currently stated Bluetooth-only Xbox use unless a later test proves otherwise.
- Hard-coding the hostname to `VimmiteV1` does not belong in a reusable image.
- Mutating `/etc/fstab` around a drive label during a general installer does not
  belong in the portable image.
- Mixing legacy `libvirtd.socket` with modular `virtqemud.socket` and
  `virtnetworkd.socket` should not be copied without choosing one supported
  architecture for the selected Fedora release.
- Enabling broad RPM Fusion repositories, performing `--allowerasing` swaps, and
  deleting unrelated repository files are mutable-workstation techniques rather
  than a clean image design.
- Running as root while modifying and recursively changing ownership of a user's
  home is fragile and inappropriate for image composition.
- Destructive Neovim cache/config removal and automatic
  `flatpak uninstall --unused` are not acceptable image or post-install defaults.
- Fetching “latest” assets at install time without checksums or pins is not
  reproducible.
- The active Zsh function backs up any existing `.zshrc` before its idempotency
  check, so reruns replace the user's configuration rather than converge safely.
- Removing Elisa and Dragon merely because the old script disliked them should
  not be inherited without a current package-conflict or user requirement.
- Snapper configuration aimed at a mutable live root is not a direct fit for an
  image-based atomic system. Deployment rollback and user-data backup/snapshots
  must be designed separately.

## Machine-specific or post-install

- The `gamedrive` label, mount point, filesystem, and mount options belong to the
  Ryzen AI MAX machine's post-install profile. General removable-media
  automounting remains a shared desktop capability.
- ROCm/AI tooling and any large TTM memory tuning belong to the AI workstation,
  not the shared AMD/Intel image. Containerized or application-bundled delivery
  remains preferable where it satisfies the workload.
- Moonlight and Sunshine are optional post-install components.
- Lutris and Heroic are optional Flatpaks to add later through Bazaar rather
  than image requirements.
- Wake-on-LAN and SSH are opt-in post-install components.
- Personal directories such as `~/dev`, `~/sync`, and the archived
  `~/ProtonDrive` hierarchy are user state, not image content.

## Needs discussion or targeted verification

- Whether the fixed PipeWire quantum configuration produces a real benefit for
  the user's workloads; it should not be described as universally optimal.
- The microphone-volume block is confirmed as useful on the HyperX host. The
  prior live inspection showed Vesktop reporting
  `application.process.binary = "vesktop.bin"` and `application.name =
  "vesktop"`. Equibop replaced Vesktop, so a real Equibop call must confirm the
  new live identity and volume behavior. The user path unit remains an explicit
  opt-in through `ujust hyperx-mic enable`.
- Personal-data backup uses encrypted Restic repositories and a tested restore
  drill, separately from bootloader OS rollback. Re-downloadable model weights,
  game installations, containers, and caches are excluded by default; see
  `docs/personal-data-backup.md` for the selected policy.
- Whether Anki, Element, LibreWolf, Video Downloader, Strawberry, Spotify, or
  KWallet Manager from older Vimmite revisions are still wanted.
- Neovim configuration is intentionally deferred. Install Vim and Neovim but do
  not port or overwrite an editor configuration.
- Whether the `bluetooth.disable_ertm=1` kernel argument is still needed for the
  Bluetooth Xbox controller on current kernels.
- Which file-sharing tools are actively used and whether server components are
  needed or only clients.

## Initial gap conclusion

Vimmite was primarily a mutable Fedora workstation bootstrap, not the source of
the current Bazzite experience. Its strongest migration candidates are intent:
virtualization, Steam device permissions, multimedia, host utilities,
fonts, shell ergonomics, and a handful of applications. The replacement gaming
stack must be designed mainly from the observed Bazzite dependency inventory and
current upstream sources, not reconstructed from Vimmite.
