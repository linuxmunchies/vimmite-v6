# Post-install profiles

The common image does not guess which machine it is running on. Optional or
machine-specific behavior is exposed through `ujust` and remains off until the
user explicitly enables it.

For a new installation, start with:

```bash
ujust vimmite-setup
```

This guided menu reports whether each option is enabled and how to undo it. It
covers desktop appearance, a development Distrobox, gaming and streaming,
RamaLama and Strix Halo AI/model storage, virtualization, SSH/Wake-on-LAN,
automounting, and the HyperX helper. Run `ujust --choose` to browse the
underlying recipes, or use the commands below directly.

## Health check and support evidence

```bash
ujust vimmite-doctor
ujust vimmite-support-bundle
```

Doctor checks the signed image origin and deployment state, both Vulkan
architectures, gaming tools, containers, libvirt, Flatpak and Homebrew
reconciliation, model storage, and optional services. A failure exits nonzero;
disabled opt-in services are reported as healthy optional state.

The support command writes a timestamped, mode-0600 archive in the current
directory. It includes a serial-number-free hardware summary, atomic deployment
state, failed services, focused service logs, current-boot kernel warnings, and
previous-boot errors when available. It does not read home-directory contents,
browser state, environment variables, or the unrestricted journal. A final
redaction pass replaces usernames, home paths, IP and MAC addresses, URL
credentials, and common secret fields. Review the archive before sharing it;
automated redaction is intentionally defense in depth, not a guarantee.

## Common user setup

```bash
ujust setup-zsh
ujust setup-virtualization
```

New accounts receive Zsh and the image-baked Zim module tree automatically.
`setup-zsh` is for upgraded accounts and preserves existing `.zshrc` and
`.zimrc` files. To also select Zsh as the login shell, run `ujust setup-zsh
true`; every retained deployment must continue to include `/usr/bin/zsh` for
rollback-safe login.

`setup-virtualization` enables libvirt's modular sockets and default NAT
network. Administrators in `wheel` are authorized by the image's
polkit rule, so a separate group change and logout are not required. The command
also grants the `qemu` service account traversal-only access to your private
home directory so ISO images selected from `~/Downloads` can be opened.

## Development box

```bash
ujust vimmite-dev create
ujust vimmite-dev enter
ujust vimmite-dev doctor
```

The build uses the image-shipped Containerfile and Distrobox assemble manifest,
not mutable package layering on the host. The box includes the common compiler,
header, debugger, Git/GitHub, ripgrep/fzf, Python/uv, Node/npm, and Rust/Cargo
baseline. Zed and desktop launches bridge back to the host; Neovim runs inside
the box; the shared home provides Git configuration and credentials; and the
current SSH agent socket is forwarded.

Use `ujust vimmite-dev update` after the definition changes. It replaces the
container filesystem but retains the shared home. `ujust vimmite-dev remove`
removes the container after confirmation and keeps both shared files and the
reusable local image. Project-specific language versions belong in `mise.toml`,
`uv.lock`, language-native project files, or `.devcontainer/`, not in the host
image. See the [complete development-box guide](development.md).

## RamaLama

```bash
ujust ramalama
```

Setup, pulling, listing, and running share this one command. The menu installs
the CLI, pulls catalog models, lists the local store, and starts a Vulkan run.
Install and setup are the same action: a user-local virtual environment in
`~/.local/share/ramalama-cli`, with `ramalama` on `~/.local/bin`. Setup does
not download weights.

Pulls can come from Hugging Face or from the public SMB share `//10.1.1.5/ai`
(Unraid `/mnt/user/ai`, guest access). Automatic mode copies a catalog GGUF
from the NAS when it is present and otherwise uses Hugging Face. Qwen 3.5
35B-A3B, Ornith 1.5 9B, Gemma 4 26B-A4B, and Granite 4.2 8B currently live on
that share; the remaining catalog models still come from Hugging Face unless
you browse other GGUFs on the NAS. Override the share with `RAMALAMA_NAS_HOST`,
`RAMALAMA_NAS_SHARE`, `RAMALAMA_NAS_USER`, and `RAMALAMA_NAS_PASS`.

```bash
ujust ramalama setup
ujust ramalama pull              # source and model menus
ujust ramalama pull auto all     # NAS when the file exists, otherwise Hugging Face
ujust ramalama pull nas qwen
ujust ramalama pull hf liquid
ujust ramalama run qwen
ujust ramalama list
ujust ramalama smoke
```

Pulling every catalog model from Hugging Face needs at least 145 GiB free in
the model store (by default `~/ai/models`). Set
`RAMALAMA_STORE=/path/on/a/large/disk` to relocate that store. `ujust ramalama
smoke` needs the Liquid model already local. Previous `ramalama-setup` and
`ramalama-pull-*` names still work as hidden aliases.

## Strix Halo local AI

Ryzen AI MAX/`gfx1151` systems have a separate Distrobox-based llama.cpp path:

```bash
ujust strix-halo-ai
```

The single menu manages stable Vulkan RADV and ROCm toolboxes, downloads the
selected Qwen and Muse GGUFs into the shared `~/ai/models` convention, installs
host-facing llama.cpp commands, and runs GPU diagnostics. It refuses other AMD
GPUs; use RamaLama on those systems. See the dedicated
[Strix Halo AI guide](strix-halo-ai.md) for backend details, wrapper defaults,
Pi Agent configuration, updates, removal, and troubleshooting.

## Lossless Scaling

The `lsfg-vk` layer is installed, but frame generation still requires the
purchased Windows Lossless Scaling application in the native Steam library.
Use `lsfg-vk-ui` to select its `Lossless.dll` and configure game profiles.

The upstream default configuration includes a `vkcube` test profile. Until the
DLL is installed, bypass that profile when checking the baseline Vulkan stack:

```bash
DISABLE_LSFG=1 vkcube
```

## Labeled internal drive automount

```bash
ujust automount status
ujust automount enable
```

This opts the machine into Universal Blue's service for labeled, non-removable
Btrfs/ext4 partitions. It mounts eligible drives under `/run/media/system` and
does not alter `/etc/fstab`. It is intended for the Ryzen AI MAX host's
`gamedrive` disk and is disabled by default elsewhere.

## Streaming

```bash
ujust install-streaming moonlight
ujust install-streaming sunshine
# or
ujust install-streaming both
```

These are per-user Flatpaks. Sunshine also runs the upstream-required
`additional-install.sh` host integration; reboot before testing Wayland capture,
audio, mouse, and controller input.

## SSH and Wake-on-LAN

```bash
ujust ssh-server enable
ujust wake-on-lan
ujust wake-on-lan eth0 enable
```

The SSH command enables `sshd` and the firewalld SSH service. Confirm key or
password authentication locally before depending on remote access.

The Wake-on-LAN command lists candidate interfaces when no interface is given.
It verifies magic-packet support and updates the active NetworkManager wired
connection. Firmware settings and power-state support must still be checked on
each machine.

## Ryzen AI MAX+ 395 legacy memory profile

```bash
ujust setup-ai-max status
ujust setup-ai-max apply
```

The apply path refuses to run unless both the Ryzen AI MAX+ 395 CPU and the
GMKtec NucBox EVO-X2 DMI identity match. It removes `iommu=off`, explicitly
enables AMD IOMMU, and restores the former large TTM/GTT values in a new atomic
deployment. The GTT argument is deprecated and is retained only as a temporary
compatibility setting pending real AI workload tests. Use
`ujust setup-ai-max undo` to remove the profile.

Do not use this profile on the Ryzen 6550U or Intel/Arc machines.
