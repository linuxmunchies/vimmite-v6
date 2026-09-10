# Vimmite V6 physical test checklist

Record the image digest, machine, firmware version, Secure Boot state, and test
date for every run. Use this checklist to record hardware confidence and known
limitations; it does not gate automatic image publication.

## Hardware acceptance matrix

Record a link or path to the completed run notes in the Evidence column. All
three rows describe the intended coverage; static image checks do not satisfy
a physical row.

| System | Required coverage | Status | Evidence / known limitations |
| --- | --- | --- | --- |
| AMD portable system | Common installation, rollback, baseline, gaming, audio, controllers, and virtualization | [ ] Open | Not yet recorded |
| Strix Halo system | Common coverage plus the complete local-AI and opted-in workstation profiles | [ ] Open | Not yet recorded |
| Intel/Arc system | Common installation, rollback, baseline, Intel Vulkan/gaming, audio, and virtualization | [ ] Open | Not yet recorded |

Mark a row complete only when it has physical evidence, and record remaining
unchecked items as known limitations. Pushes and scheduled builds publish
automatically; completing this matrix is not a workflow approval step.

## Build artifact gate

- [x] `bluebuild validate recipes/vimmite.yml` passes.
- [x] The repository has its `SIGNING_SECRET` configured for image publication.
- [ ] A clean `bluebuild build --no-sign recipes/vimmite.yml` passes for the
      current change set.
- [x] The image uses `ghcr.io/ublue-os/kinoite-main:44` and Fedora's standard
      kernel, not an OGC/Bazzite kernel.
- [x] Firefox is present; Gamescope and NVIDIA-specific packages are absent.
- [ ] LACT, input-remapper, and their enabled services are present.
- [ ] `brew` initializes successfully through BlueBuild's native module, including `hf --help`.
- [ ] No EVDI or DisplayLink packages, modules, services, scripts, or helpers
      remain in the image.
- [x] Steam, 32/64-bit MangoHud, controller rules, and `lsfg-vk` are present.
- [x] `modprobe -c` reports `options hid_apple fnmode=2`, and the image
      initramfs contains the setting.
Verified locally on 2026-08-25 against image
`sha256:71fedc25c0c0fa5058770aef2575fbca2535688200562bffed17d556b0e24362`.
The previous artifact used kernel `7.1.10-200.fc44.x86_64`; `dnf check` also
completed successfully. Re-run this gate for the current change set before
installation. Static artifact verification is not approval to install or
rebase.

## Installation and rollback

- [ ] Install on the explicitly designated test machine without changing the
      current primary host.
- [ ] Installer completes without the previously observed grey screen.
- [ ] First reboot reaches SDDM and Plasma on every connected native display.
- [ ] After the first image update, `rpm-ostree status` retains the prior
      deployment and it can be selected from the boot menu.
- [ ] `rpm-ostree status` reports the expected signed image origin/digest.
- [ ] Btrfs root/home layout and encryption match the chosen installer plan.

## Portable baseline on every machine

- [ ] `ujust vimmite-setup` opens every Phase 2 category, accurately reports
      enabled state, and provides a working reversal path for each optional
      change.
- [ ] `ujust vimmite-doctor` reports the signed origin, pending deployment
      state, 64/32-bit Vulkan, gaming/container/virtualization components,
      reconciliation jobs, model storage, and optional services with accurate
      green/warning/failure severity.
- [ ] `ujust vimmite-support-bundle` creates a mode-0600 archive whose contents
      have been manually inspected for usernames, home paths, IP/MAC addresses,
      credentials, browser state, and unrelated journal entries.
- [ ] The installer/live Plasma session and a newly created user's first desktop
      use the Vimmite wallpaper and Vimmite Graphite color scheme.
- [ ] SDDM and the Plasma lock screen use the Vimmite lock artwork at native and
      mixed-DPI resolutions without stretching, clipping credentials, or
      reducing contrast.
- [ ] Kickoff uses the Vimmite mark; Fastfetch renders the Vimmite ASCII logo;
      Kitty uses JetBrains Mono Nerd Font, 12 px padding, and the Vimmite palette.
- [ ] Wi-Fi, Ethernet, Bluetooth, audio, camera, keyboard, and touchpad work.
- [ ] Suspend/resume succeeds ten consecutive times, including an overnight
      suspend where practical.
- [ ] Boot offline, observe a failed Flatpak reconciliation, connect Wi-Fi, and
      verify all required Flatpaks install without rebooting.
- [ ] Firefox, Brave, Bitwarden, Warehouse, and LocalSend launch.
- [ ] A new user starts in Zsh with working Zim and `~/dev`, `~/sync`, and `~/ai`.
- [ ] Zsh/Zim setup preserves pre-existing dotfiles on a rerun.
- [ ] Distrobox can create, enter, update, and remove a disposable test box.
- [ ] `ujust vimmite-dev manifest` produces a rootless assemble plan for only
      `vimmite-dev`, and `create` builds it without layering host packages.
- [ ] `ujust vimmite-dev doctor` passes C and Rust compilation, Python native
      module, JavaScript, CLI-tool, Neovim, Zed bridge, desktop-launch, Git
      configuration, and SSH-agent checks.
- [ ] `ujust vimmite-dev update` replaces container-only state while retaining
      a sentinel project in the shared home; `remove` retains that sentinel and
      the reusable local image.
- [ ] A sample Python project uses `uv.lock`, a TypeScript project uses a local
      compiler and lockfile, and a mise/devcontainer project selects declared
      Node, Python, Go, and Rust versions without host package layering.
- [ ] No AI MAX TTM/GTT arguments appear on Ryzen 6550U or Intel systems.
- [ ] An encrypted Restic backup and restore drill passes for the selected
      personal-data scope; record repository location, snapshot ID, restored
      sample, and the intentional exclusions without recording credentials.

## Strix Halo local AI

- [ ] `ujust strix-halo-ai` opens the 15-choice `ugum` menu.
- [ ] Unsupported AMD hardware is refused unless the documented diagnostic override is set.
- [ ] Vulkan uses `vulkan-radv`, `/dev/dri`, `keep-groups`, and unconfined seccomp.
- [ ] ROCm uses `rocm-10.0`, `/dev/dri`, `/dev/kfd`, `keep-groups`, and unconfined seccomp.
- [ ] Both `llama-cli --list-devices` calls report gfx1151/Radeon 8050S or 8060S.
- [ ] The version menu option reports the toolbox image and `llama-server` build for each installed backend.
- [ ] Host and both containers see the same sentinel below `~/ai/models`.
- [ ] Every host wrapper selects its intended backend and supplies overridable defaults.
- [ ] A localhost llama-server responds from the host on a non-conflicting test port.
- [ ] Bare Vulkan and ROCm server wrappers enter router mode rooted at `~/ai/models` and list the three managed IDs.
- [ ] Qwen 3.6 and 3.8 use `draft-mtp` with `spec-draft-n-max = 3`; Muse has no MTP preset.
- [ ] Update/recreate and Remove leave the model sentinel and downloaded weights intact.
- [ ] Reinstall after removal restores the backend and host wrappers cleanly.
- [ ] No host ROCm/llama.cpp package, udev mode rule, kernel argument, or BIOS change is introduced.

## Graphics and gaming

- [ ] `vulkaninfo` identifies the intended AMD or Intel GPU without software
      rendering.
- [ ] Native Steam launches and sees internal/external game libraries.
- [ ] A native Linux game and a Proton game launch.
- [ ] MangoHud works for both a 64-bit game and a 32-bit/Proton title.
- [ ] The EPOMAKER EA75 function row behaves normally with `fnmode=2`.
- [ ] ProtonPlus can install a compatibility tool visible to Steam.
- [ ] Bottles creates and launches a disposable test bottle.
- [ ] Lossless Scaling's Vulkan layer is discoverable and passes one real game
      test. Gamescope is not required for acceptance.

## Controllers

- [ ] The Chicken Run receiver enumerates in its `054c:09cc` PlayStation mode.
- [ ] Steam Input sees buttons, sticks, triggers, touchpad, motion, and rumble.
- [ ] Reconnect the receiver and repeat after resume.
- [ ] If the receiver exposes `3537:0575`, capture `udevadm`, `libinput`, and
      Steam Input results before adding a workaround.
- [ ] Pair and test the primary controller over Bluetooth.
- [ ] Pair and test an Xbox controller over Bluetooth.
- [ ] Test a Steam Controller when hardware becomes available.

## Audio and microphone

- [ ] `ujust hyperx-mic status` reports disabled before explicit opt-in.
- [ ] `ujust hyperx-mic enable` enables the per-user path unit and is safe to rerun.
- [ ] HyperX playback and capture appear after receiver reconnect and resume.
- [ ] The microphone starts at 90%.
- [ ] During a real Equibop call, record its PipeWire-Pulse identity with
      `pactl list source-outputs`, and confirm `application.process.binary` and
      `application.name` match `10-mic-lock.conf`.
- [ ] Equibop cannot lower the source volume during calls, input-device
      changes, receiver reconnect, or resume. Retest after an Equibop update.
- [ ] OBS, browser capture, and normal volume controls still work.

## Virtualization and optional profiles

- [ ] virt-manager connects to `qemu:///system` as the non-root user.
- [ ] The Arch ISO in `~/Downloads` reaches its boot menu with KVM, UEFI, and
      the default NAT network.
- [ ] Create a UEFI VM, a TPM-backed VM, and a NAT-connected VM.
- [ ] VM shutdown and host suspend/resume do not leave stale libvirt state.
- [ ] Labeled-drive automount mounts `gamedrive` under `/run/media/system` only
      on the opted-in host.
- [ ] Moonlight client streaming works if installed.
- [ ] Sunshine Wayland capture, audio, and remote controller input work if
      installed.
- [ ] SSH and Wake-on-LAN remain disabled until explicitly enabled, then pass a
      same-LAN test and can be disabled again.
- [ ] LACT connects to `lactd`; input-remapper lists devices and answers its
      control handshake; both services survive reboot.
- [ ] `ujust ramalama` opens the combined setup/pull/run menu. Pulling from
      Hugging Face and from the public `//10.1.1.5/ai` SMB share both work;
      `setup` does not download weights.

## Evidence to collect on failure

Capture `rpm-ostree status`, `journalctl -b`, the previous boot journal when a
resume fails, `inxi -Fz`, `lsusb`, `lspci -nnk`, and the exact command/output for
the failing component. Avoid copying credentials or unrelated user data.

## Accepted limitations

Record each known limitation with its owner, affected systems, and workaround
(if any). Unchecked items remain unverified; automatic publication does not
turn them into passing hardware results.

- None recorded.
