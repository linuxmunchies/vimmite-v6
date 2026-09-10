# Vimmite V6 investigation

This is the working record for the Vimmite V6 audit and rebuild. It records
observations separately from decisions and keeps unresolved design work visible.

## Confirmed scope and decisions

- Keep KDE Plasma.
- Produce one portable x86_64 image for AMD and Intel systems. Nvidia-specific
  packages, configuration, workarounds, and testing are out of scope.
- Target examples include Ryzen 5 6550U/Radeon 660M, Ryzen AI MAX+ 395/Radeon
  8060S, and Intel Core Ultra 7 140V/Arc graphics systems.
- Retain Firefox from the base image so a browser is always available. Brave is
  preferred as a Flatpak rather than an RPM from an additional repository.
- Keep every GUI application currently declared in the recipe available on
  every machine. Vim and Neovim are required host applications, and Zed is
  required; editor configuration is outside the current image scope.
- Prefer Zsh with Zim for the interactive shell. Python, Go, and Rust development
  environments can live in Distrobox containers.
- Preserve Steam, ProtonPlus, Bottles, Distrobox, MangoHud, Lossless Scaling,
  and controller support. Moonlight and Sunshine are optional post-install
  components.
- Lutris and Heroic are optional Flatpaks to install later through Bazaar; do
  not expand the base image's gaming R&D to integrate them.
- Controller coverage must include Xbox controllers, the Steam Controller, and
  DualShock/DualSense-compatible controllers. The PlayStation-compatible
  controller is the primary device and therefore the primary acceptance case.
  Its 2.4 GHz receiver is the primary connection path, with Bluetooth also
  required.
- Preserve virt-manager and provide the host virtualization backend it needs.
- Wake-on-LAN and SSH are post-install options, not globally enabled defaults.
- Preserve automatic removable/game-drive mounting where practical. Any fixed
  second-drive layout belongs in the Ryzen AI MAX host's post-install profile.
- Retain Fira Code and JetBrains Mono Nerd Fonts.
- Use Btrfs and preserve atomic deployment rollback from the bootloader. Treat
  personal-data snapshots and backups as a separate design question; Snapper is
  not currently a requirement.

## Current repository observations

- `recipes/vimmite.yml` now inherits `ghcr.io/ublue-os/kinoite-main:44`; it is
  the sole supported Vimmite V6 image recipe.
- The replacement is split into explicit hardware, host package, gaming,
  virtualization, configuration, Flatpak, and signing modules.
- The locally installed BlueBuild CLI validates the recipe, and a complete
  unsigned local build passed on 2026-08-25.
- Artifact inspection confirmed the standard Fedora kernel, Firefox, Steam,
  both MangoHud architectures, AMD/Intel Vulkan userspace, controller
  rules, QEMU/libvirt, the requested editors, and the intended Flatpak manifest.
- Gamescope and NVIDIA-specific RPMs are absent. The inherited
  `fedora-multimedia` repository supplies Steam, avoiding an additional Steam
  repository in this project.
- The PipeWire-Pulse rule retains Vesktop's previously observed process
  properties and adds Equibop's packaged executable identity. A real Equibop
  call must confirm its live properties and volume behavior. The HyperX
  microphone path unit restores 90% when explicitly enabled through `ujust
  hyperx-mic enable`; it is inactive by default.
- The workflow builds and publishes the Kinoite-based Vimmite V6 recipe.

## Current host observations

- The host is a signed Vimmite2 deployment built on Bazzite 44/Kinoite with an
  OGC kernel. The only detected local layered RPM is ChatGPT.
- Bazzite supplies substantial undeclared functionality, including Steam,
  Gamescope, MangoHud, controller support, codecs, Distrobox/Toolbox, ujust,
  media automounting, and system tuning. These become explicit migration items
  when Bazzite is removed as the base.
- Software present outside the current recipe includes Brave, Jellyfin Desktop,
  OpenMW, virt-manager, ProtonPlus, Stremio, FileZilla, LM Studio, an amdtop
  export from Distrobox, StreamingServiceLauncher, and a Lossless Scaling UI.
- The host has Zim configuration, but Bash remains the login shell.
- virt-manager is present as a Flatpak, but the inspected host did not have a
  usable libvirt/QEMU backend.
- The game drive is automatically mounted under `/run/media/system/gamedrive`.
- Sunshine and a host ROCm stack were not detected in the initial
  inventory.
- The microphone lock is required but currently broken. Live inspection found
  Vesktop using `application.process.binary = "vesktop.bin"` and
  `application.name = "vesktop"` while the shipped PipeWire rule matches neither.
  The active HyperX Cloud Alpha Wireless source had already fallen to 76%; the
  desired fixed level is 90%.
- A live user-level test rule was installed at
  `~/.config/pipewire/pipewire-pulse.conf.d/90-vesktop-mic-lock.conf`, the
  PipeWire-Pulse service was restarted, and the HyperX source was set to 90%.
  The corrected rule is present in the merged configuration and is provisionally
  accepted. Reopen the issue and collect live properties again if the volume
  begins falling in future use.

## Controller observations

- The connected Guangzhou Chicken Run 2.4 GHz receiver currently enumerates as
  USB `054c:09cc`, the identity used by a Sony DualShock 4 v2.
- The upstream `hid_playstation` kernel driver claims it and exposes a joystick,
  motion sensors, touchpad, force feedback, and hidraw access. No custom driver
  is required in this mode.
- udev identifies it as `Sony_DualShock_4` and grants desktop-user access. The
  current host has matching rules from both `steam-devices` and
  `ublue-os-udev-rules`; the replacement must preserve the needed access rule
  without blindly copying duplicate Bazzite packages.
- An earlier boot log shows a Chicken Run device on the same USB port using
  generic HID identity `3537:0575`. This may be an alternate receiver/controller
  mode and should be tested rather than assuming it always uses PlayStation mode.
- The current host also carries the out-of-tree `xone` kernel module. It is not
  involved with this PlayStation-mode controller. Xbox controllers are used over
  Bluetooth rather than Microsoft's dedicated wireless adapter, so `xone` is a
  removal candidate unless the remaining audit finds another concrete need.
- A Steam Controller is planned but is not currently available for physical
  validation; keep its support in scope and defer the hardware acceptance test.

## Hardware-specific findings

The current Ryzen AI MAX+ 395 host has these custom kernel arguments:

```text
bluetooth.disable_ertm=1
kvm.ignore_msrs=1
kvm.report_ignored_msrs=0
amdgpu.gttsize=122880
ttm.pages_limit=30720000
iommu=off
```

Observations:

- `iommu=off` prevents the AMD XDNA driver from initializing and coincides with
  MediaTek Wi-Fi DMA initialization errors on this host.
- `amdgpu.gttsize` emits a deprecation warning on the current kernel.
- `ttm.pages_limit=30720000` sets a 120 GiB page limit and is an unusually
  large, AI-workload-specific setting.

Decisions:

- Do not place the TTM/GTT or other Ryzen AI MAX tuning in the portable image.
- Do not globally disable IOMMU. The replacement installation will use enabled
  firmware/platform IOMMU behavior.
- Put any justified Ryzen AI MAX memory tuning in an explicit, reversible
  machine-specific post-install profile. Re-evaluate the deprecated GTT argument
  instead of copying it forward.
- Other AMD and Intel machines keep upstream kernel memory/IOMMU defaults unless
  testing demonstrates a concrete need.

Live comparison on the existing Vimmite2 AI MAX host:

- An `iommu=off` boot failed XDNA initialization with "Running without IOMMU
  not supported", produced an MT7925 DMA-address overflow, and ended with Wi-Fi
  hardware initialization failing.
- After changing the existing host to `iommu=on`, the next boot created 40 IOMMU
  groups, initialized `amdxdna`, exposed `/dev/accel/accel0`, and initialized the
  MT7925 Wi-Fi device without those DMA errors.

## Flatpak notification finding

The existing Vimmite2 deployment runs `user-flatpak-setup.timer` 30 seconds
after the user session starts. Its generated configuration declares a user
Flathub remote with an empty install list and notifications enabled, producing
the repeated "finished automated installation of 0 user Flatpaks" message.
Vimmite V6 retains the user Flathub remote for optional applications but explicitly
sets `notify: false` for that empty user scope. System Flatpak reconciliation and
its useful notifications remain enabled.

## Reported reliability problems to reproduce

- On two devices, the installer completed and then the display became entirely
  grey until the first reboot. It did not recur after reboot.
- Suspend occasionally struggles or fails to resume reliably.

These are test cases, not yet assigned causes. Installer graphics, first-boot
state, kernel/display drivers, and suspend logs all remain in the
investigation scope.

## Open architecture work

- Complete the physical checklist on AMD iGPU, Intel/Arc, and Ryzen AI MAX
  hardware, including first reboot, suspend/resume, gaming, controller,
  and virtualization acceptance tests.
- Test the Ryzen AI MAX profile with a real AI workload before deciding whether
  the deprecated GTT argument should survive.
- Decide on a personal-data backup policy separately from atomic deployment
  rollback.

The initial Vimmite classification is maintained in
[Vimmite migration inventory](vimmite-migration.md).
