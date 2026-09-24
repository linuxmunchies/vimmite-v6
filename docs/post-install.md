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
network. The image adds local interactive users to `video`, `render`, `kvm`,
and `libvirt` on boot, and still authorizes `wheel` for `org.libvirt.unix.manage`
through polkit. A new graphical or SSH login is required before the extra
groups appear in an already-open session. The command also grants the `qemu`
service account traversal-only access to your private home directory so ISO
images selected from `~/Downloads` can be opened.

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

Use `ujust vimmite-dev update` to upgrade packages in place. It retains
container-installed applications and the shared home. `ujust vimmite-dev remove`
removes the container after confirmation and keeps both shared files and the
reusable local image. Project-specific language versions belong in `mise.toml`,
`uv.lock`, language-native project files, or `.devcontainer/`, not in the host
image. See the [complete development-box guide](development.md).

## AI hub, installs, and updates

Use one entry point for AI setup and maintenance:

```bash
ujust ai
```

The hub groups coding harnesses, ChatGPT Desktop, Claude Desktop, ComfyUI,
RamaLama, and the Strix Halo managers. The first-run setup menu opens this
same hub, so there is no second AI-specific menu to remember.

Every install screen offers:

- **Distrobox container: `vimmite-dev` (recommended)** — creates the box after
  confirmation when it is not already present, then exports desktop apps back
  to the host application menu when possible.
- **Host installation** — installs the CLI into the user environment, layers
  desktop RPMs into the Atomic host, or creates the generic ComfyUI virtual
  environment under the user’s home directory.

The direct compatibility commands remain available for automation, including
`ujust install-ai-cli <tool>`, `ujust strix-halo-ai`, and
`ujust strix-halo-comfyui`. The unified update entry point is:

```bash
ujust ai-update
ujust ai-update check
```

It can update all installed AI software or an individual area: coding
harnesses, `vimmite-dev`, generic and Strix Halo ComfyUI, Strix Halo llama.cpp
containers, and installed ChatGPT/Claude desktop RPMs. Host RPM updates on
Vimmite are scheduled through `rpm-ostree`; a reboot may be required.
Strix Halo container updates compare the pulled image ID with the installed
container and skip recreation when they match. npm-based Codex and DSH updates
compare the installed package with the configured registry tag; ChatGPT Desktop
skips installation when its downloaded RPM matches the installed version.
Use each Strix manager's `refresh` action to intentionally recreate a container
from an unchanged image.
`check` reports available updates without changing installed applications or
containers. It may refresh package metadata or cache a pulled image to compare
its exact ID. Installers that do not publish a reliable version check are
reported as such and run only when an update is requested.

The coding-harness choices are:

| Tool | Installer or npm package |
| --- | --- |
| Codex | `@openai/codex` |
| Grok Build | <https://x.ai/cli/install.sh> |
| Pi | <https://pi.dev/install.sh> |
| OMP / Oh My Pi | <https://omp.sh/install> |
| Claude Code | <https://claude.ai/install.sh> |
| DSH / DeepSeek Harness | `@deepseek-ai/dsh` (`alpha` tag) |
| OpenCode | <https://opencode.ai/install> |
| Hermes Agent | <https://hermes-agent.nousresearch.com/install.sh> |

npm-published harnesses install from the `latest` dist-tag, except DSH, whose
`latest` tag trails its real development line; it installs from `alpha`. Set
`VIMMITE_AI_TAG_<CLI>` to choose another tag or an exact version, for example
`VIMMITE_AI_TAG_DSH=latest ujust install-ai-cli dsh container` or
`VIMMITE_AI_TAG_CODEX=0.9.0 ujust install-ai-cli codex container`.

Arguments after `--` reach the upstream installer unchanged, which is useful
for the longer installs:
`ujust install-ai-cli hermes container -- --skip-browser`.

DSH installation does not start its web server; launch it afterward with
`dsh web`. The upstream quick start is `npx @deepseek-ai/dsh web`
([DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness)).
Hermes Agent installs its `hermes` launcher in `~/.local/bin`; run `hermes
setup` after installation to choose a provider.
Follow each installer's PATH guidance and open a new terminal before use.
Authentication is handled by each tool when you launch it. For GPU-tuned
Strix Halo image generation, use the hub’s **Strix Halo GPU ComfyUI** path;
the generic ComfyUI installer is portable and uses the selected host or
`vimmite-dev` Python environment.

To undo the npm installations, run
`npm uninstall -g --prefix "$HOME/.local" @openai/codex` or
`npm uninstall -g --prefix "$HOME/.local" @deepseek-ai/dsh`.
For script-installed tools, follow the upstream uninstall instructions for
the installation location reported by the installer; retain configuration
and credentials unless you intend to remove them too.

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
from the NAS when it is present and otherwise uses Hugging Face. All eight
catalog models currently live on that share. Override the share with
`RAMALAMA_NAS_HOST`, `RAMALAMA_NAS_SHARE`, `RAMALAMA_NAS_USER`, and
`RAMALAMA_NAS_PASS`.

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

Ryzen AI MAX/`gfx1151` systems have separate Distrobox-based llama.cpp and
ComfyUI paths:

```bash
ujust strix-halo-ai
```

The single menu manages stable Vulkan RADV and ROCm llama.cpp toolboxes plus
stable and experimental upstream ComfyUI containers. It downloads only models
the user explicitly selects, can upload those files to the NAS share, and keeps
ComfyUI models, inputs, outputs, workflows, and settings in the user's home.
It also runs GPU diagnostics. It refuses other AMD GPUs; use RamaLama on those
systems. See the [Strix Halo AI guide](strix-halo-ai.md) for llama.cpp and the
[Strix Halo ComfyUI guide](strix-halo-comfyui.md) for image generation lifecycle
and storage.

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

### AI installation isolation and update failures

`ujust install-ai-cli codex host` and `ujust install-ai-cli codex container`
forward the selected target. Container CLIs use a dedicated home under
`~/.local/share/vimmite-ai/container`, including their configuration, caches,
and package directories. Launch them through `<tool>-container` (for example,
`codex-container`) so the container and its environment are selected together.
Host commands keep their normal names and paths. Existing shared CLI installs
must be reinstalled for the container target to establish this isolation.

Installs and `<tool>-container` launches attach the terminal to the container,
so upstream installers can show progress and ask questions, and the harnesses
themselves can open `/dev/tty` and run their full-screen interfaces. Run them
from a real terminal: piping either one (or running it from a script or cron)
falls back to a non-interactive container session, and a harness started that
way exits rather than drawing its interface.

Generic ComfyUI keeps independent `host` and `container` directories under
`~/.local/share/vimmite-comfyui`, each with its own checkout and virtual
environment. Both installed targets receive updates. Install and update run
`pip install -U --pre comfyui-manager` in that target's venv, and launch
passes `--enable-manager`. Use `vimmite-comfyui host` or
`vimmite-comfyui container` to choose explicitly; without a target the
launcher selects the most recently installed target. Old shared checkouts
are retained; reinstall each desired target to create its isolated
environment.

`ujust ai-update all` upgrades the development box in place, preserving desktop
RPMs. It also updates an existing managed RamaLama CLI without downloading
models. All update areas are attempted; any failure produces a nonzero exit
status. Strix llama.cpp updates pull the replacement image before removing
the old container, so failed downloads leave the existing container intact.
