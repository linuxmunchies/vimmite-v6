# Vimmite V6

<p align="center">
  <img src="docs/assets/vimmite-logo.svg" alt="Vimmite OS compass logo" width="144">
</p>

[![BlueBuild](https://github.com/linuxmunchies/vimmite-v6/actions/workflows/build.yml/badge.svg)](https://github.com/linuxmunchies/vimmite-v6/actions/workflows/build.yml)

Vimmite is my personal Fedora Atomic desktop, built around Kinoite, KDE Plasma,
and BlueBuild. It brings my gaming, development, media, and everyday tools
into one signed image for AMD and Intel PCs.

The image contains shared desktop defaults. Optional setup commands handle
things such as development containers, local AI, streaming, and remote access.
This is a personal project that friends are welcome to try; hardware coverage
and remaining checks are recorded in the [test checklist](docs/test-checklist.md).
A successful image build does not establish that every device or workload works.

## What you get

- **Desktop:** Fedora 44 Kinoite, KDE Plasma, Vimmite artwork and colors,
  Zsh/Zim, Kitty, and familiar command-line tools.
- **Gaming:** native Steam, MangoHud, 32-bit Vulkan support, ProtonPlus,
  Bottles, and the Lossless Scaling Vulkan layer.
- **Development:** Podman and Distrobox, an optional Fedora development box,
  editors, and virtualization tools.
- **Everyday apps:** browsers, messaging, productivity, media, and creative
  applications, with system Flatpaks managed from Flathub.
- **Optional profiles:** local AI, SSH, Wake-on-LAN, streaming, labeled-drive
  automounting, and hardware-specific helpers.

The [recipes](recipes/vimmite.yml) are the source of truth for packages and
services. Hardware-specific instructions and undo commands live in the
[post-install guide](docs/post-install.md). NVIDIA systems are outside this
image's intended hardware scope.

## Try it

The image is published to
[`ghcr.io/linuxmunchies/vimmite-v6-kinoite:latest`](https://github.com/linuxmunchies/vimmite-v6/pkgs/container/vimmite-v6-kinoite).
The GHCR package must be public for downloads and updates without credentials;
source-repository visibility alone does not provide that access.

Start with the [installation guide](docs/installation.md), which covers building
an ISO, installing it, or rebasing an existing Fedora Atomic desktop. ISO builds
need a Linux machine with KVM/QEMU and at least 70 GiB of free workspace. The
workflow publishes container images; it does not attach downloadable ISOs.
Back up personal files before installing or rebasing.

After booting, connect to the network so application setup can finish, then run:

```bash
ujust vimmite-setup
ujust vimmite-doctor
```

The setup menu offers optional features and their undo commands. Browse the
remaining commands with `ujust --choose`. If something fails, run
`ujust vimmite-support-bundle` and review the generated archive before sharing it.

For updates and rollback commands, see [installation and updates](docs/installation.md#updating-and-rolling-back).
Atomic rollback covers the system deployment; personal files need a separate
[backup](docs/personal-data-backup.md).

## Builds and publication

GitHub Actions builds and publishes automatically on non-documentation pushes
and the daily schedule. You can also start a build with `workflow_dispatch`.
There is no manual release-approval input. Pull requests run validation and an
image build without publishing.

Images are signed using the `SIGNING_SECRET` Actions secret. Only the public
verification key, [`cosign.pub`](cosign.pub), belongs in this repository.

```bash
cosign verify --key cosign.pub ghcr.io/linuxmunchies/vimmite-v6-kinoite:latest
```

To build the checkout locally without publishing:

```bash
bluebuild validate recipes/vimmite.yml
bluebuild build --no-sign recipes/vimmite.yml
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the local validation commands and
code conventions. Physical testing remains separate from automatic publication.

## Repository layout

| Path | Purpose |
| --- | --- |
| `recipes/` | Image recipe and grouped BlueBuild modules |
| `files/vimmite/` | Files installed into the image, mirroring the target filesystem |
| `files/vimmite/usr/libexec/` | Runtime helpers behind the setup commands |
| `files/justfiles/` | Discoverable `ujust` commands and small shell recipes |
| `files/scripts/` | Build-time installers for pinned external artifacts |
| `scripts/` | Repository validation, ISO builds, and registry login |
| `docs/` | Installation, configuration, design, and testing guides |
| `docs/history/` | Historical investigations and migration notes |
| `.github/` | Build workflow, ownership, and dependency updates |

## Guides

- [Installation and updates](docs/installation.md)
- [Optional setup and hardware profiles](docs/post-install.md)
- [Development container](docs/development.md)
- [Strix Halo local AI](docs/strix-halo-ai.md) and [model configuration](docs/strix-halo-ai-configuration.md)
- [Branding](docs/branding.md)
- [Personal-data backup](docs/personal-data-backup.md)
- [Physical test checklist](docs/test-checklist.md)
- [Architecture and dependency rationale](docs/architecture-proposal.md)

## License

[Apache License 2.0](LICENSE).
