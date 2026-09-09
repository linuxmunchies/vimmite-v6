# Vimmite development box

Vimmite keeps compiler stacks and language runtimes out of the immutable host.
The image ships a build definition and Distrobox assemble manifest instead:

```bash
ujust vimmite-dev create
ujust vimmite-dev enter
ujust vimmite-dev doctor
```

`create` builds `localhost/vimmite-dev:44` from the Fedora 44 toolbox base and
assembles the rootless `vimmite-dev` container. It is safe to rerun; use
`update` when the definition changes and the existing container must be
replaced. Replacement retains projects and configuration because Distrobox
shares the normal home directory, but packages or files written only into the
container filesystem are discarded.

The complete lifecycle is:

| Goal | Command |
| --- | --- |
| Inspect current state | `ujust vimmite-dev status` |
| Preview the assemble command | `ujust vimmite-dev manifest` |
| Build and create | `ujust vimmite-dev create` |
| Rebuild and replace | `ujust vimmite-dev update` |
| Enter interactively | `ujust vimmite-dev enter` |
| Run a command | `ujust vimmite-dev enter -- rg TODO ~/dev/project` |
| Verify tools and integration | `ujust vimmite-dev doctor` |
| Install optional mise | `ujust vimmite-dev mise` |
| Export a container GUI app | `ujust vimmite-dev export-app APP` |
| Remove the container | `ujust vimmite-dev remove` |

Removal keeps the local image and shared home. If disk space is needed, inspect
the image first with `podman image inspect localhost/vimmite-dev:44`; removing
that reusable image is a separate, explicit Podman operation.

## Included baseline

The box includes GCC/G++, Clang, CMake, Meson, Ninja, Autotools, Mold, ccache,
common C/Python headers, and the GDB, LLDB, Valgrind, strace, perf, cppcheck,
and ShellCheck diagnostic stack. Git, Git LFS, GitHub CLI, ripgrep, fzf, fd,
Neovim, tmux, curl, and common archive/build utilities are also present.

Fedora's Python, uv, Node/npm, and Rust/Cargo packages provide a usable
baseline. They are not Vimmite's answer to project versioning. Repositories
should declare versions and dependencies themselves:

- Python: commit `pyproject.toml` and `uv.lock`; use `uv sync` and `uv run`.
- JavaScript/TypeScript: commit the package-manager lockfile and keep
  TypeScript in project `devDependencies`; run it with `npx tsc` or the chosen
  package manager.
- Rust: keep dependencies in `Cargo.toml`/`Cargo.lock`; select an exact compiler
  through project-local mise configuration or a devcontainer when Fedora's
  baseline is not appropriate.
- Cross-language projects: run `ujust vimmite-dev mise`, then commit a
  project-local `mise.toml` and optional `mise.lock`.
- Projects needing stronger isolation can commit `.devcontainer/`; the box's
  `podman` command is bridged to rootless Podman on the host.

Do not put project-specific Node, Python, Go, or Rust versions into the Vimmite
host recipe or this Containerfile.

## Host integration

- `$HOME` is shared, so Git configuration, GitHub CLI state, SSH files, editor
  configuration, and projects are the same inside and outside the box.
- `SSH_AUTH_SOCK` is forwarded when the box is assembled. `doctor` warns when
  the current session does not expose a usable agent socket.
- Neovim runs inside the container, so its subprocesses see container
  compilers and language servers while retaining the shared user config.
- `zed .` invokes the host Zed Flatpak. Project paths under the shared home are
  identical on both sides.
- `xdg-open`, Flatpak, and Podman are bridged through `distrobox-host-exec`, so
  browsers, desktop files, and per-project devcontainers launch on the host.
- `git-credential-libsecret` is available inside the box; existing Git helper
  configuration and SSH credentials remain user-owned in the shared home.

The manifest follows Distrobox's supported repeated `additional_flags` and
`init_hooks` model. See the official [Distrobox assemble
documentation](https://distrobox.it/usage/distrobox-assemble/) and Universal
Blue's [container-first administration guidance](https://docs.projectbluefin.io/administration/).
