# Vimmite V6 Test Results

Test date: 2026-09-09  
Target: ThinkPad T14 Gen 4 AMD at `10.1.1.132`

## Result

The ThinkPad is operating correctly after reboot and is running the signed Vimmite V6 image. The desktop wallpaper issue was corrected and the fix persisted across reboot. No failed system or user services were found.

## Verified

- Booted deployment: signed `ghcr.io/linuxmunchies/vimmite-v6-kinoite:latest`
- Booted image digest: `sha256:b19e2f182e8922194d6a9e1310ab9cebf9de01b63b1e147d3a8e7a8c0da8e263`
- Image version: `44.20260909.1`
- Original Fedora deployment retained as a rollback
- Desktop wallpaper points to `/usr/share/wallpapers/Vimmite`
- Vimmite wallpaper package is valid and recognized by Plasma
- First-login wallpaper service is enabled and completed successfully
- First-login sentinel was created, confirming successful one-time application
- Lock-screen wallpaper configuration remains functional
- Plasma Wayland session and Plasma Login Manager are active
- SSH is enabled, active, and survived reboot
- No failed system units
- No failed user units
- NetworkManager and Bluetooth are active
- PipeWire, WirePlumber, and the desktop portal are active
- AMD Radeon 780M Vulkan works with the expected 64-bit and 32-bit components
- Steam, MangoHud, and GameMode are available
- Podman and Distrobox are available; rootless Podman responds
- Libvirt QEMU and network sockets are active and usable
- LACT and Input Remapper are active
- Flatpak reconciliation and user-installation integrity checks passed
- LUKS, Btrfs, SMART storage health, camera detection, audio detection, and TPM checks passed during the hardware audit
- Temporary GitHub credentials were removed and are absent from `/run/ostree/auth.json` and `/etc/ostree/auth.json`

`ujust vimmite-doctor` completed with **0 failures and 1 warning**. The warning is only that the optional `~/ai/models` directory has not been created.

## ISO Validation

The generated `vimmite-v6-kinoite-verified.iso` passed:

- SHA-256 checksum verification
- Embedded installation-media checksum verification
- BIOS boot catalog inspection
- UEFI boot catalog inspection
- QEMU/KVM BIOS boot smoke test
- QEMU/KVM UEFI boot smoke test

## Source and CI

The reviewed changes were pushed to the private repository on `main`:

- `c95d417` — Fix installer origin and Plasma first-login defaults
- `22446a7` — Document private GHCR update authentication

GitHub Actions successfully built the Vimmite V6 image in run `34392173605`.

Local syntax, formatting, metadata, configuration, and first-login behavior checks passed. Secret scanning found no committed passwords, tokens, or private keys.

The following local files were deliberately excluded from the commits:

- `ISO-FAIL.MD` — stale and inconsistent with the current VM-based ISO workflow
- `LockScreen.png` — duplicate of the tracked wallpaper asset
- `VimmiteOS.png` — duplicate of the tracked wallpaper asset

## Remaining Operational Requirement

Because the GHCR package is private, unattended `rpm-ostree` updates cannot authenticate without persistent registry credentials. A dedicated classic GitHub personal access token limited to `read:packages` should be installed according to the repository README. The broader GitHub CLI token used for the one-time rebase was intentionally not persisted.

Alternatively, the container package can be made public while keeping the source repository private.

## Firmware Notice

Lenovo system firmware version `0.1.50` is available; the ThinkPad currently has `0.1.49`. The update is marked high urgency by LVFS and was not installed during this audit.

## Tests Requiring Physical Interaction

The following were not fully provable through remote access:

- Repeated suspend and resume cycles
- Real microphone and camera calls
- Bluetooth device and controller pairing
- A complete bare-metal reinstall using the newly generated ISO

