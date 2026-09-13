# Strix Halo local AI

Vimmite provides dedicated llama.cpp and ComfyUI paths for AMD Ryzen AI MAX
"Strix Halo" APUs (`gfx1151`). The llama.cpp subsystem uses stable images from
[kyuz0/amd-strix-halo-toolboxes](https://github.com/kyuz0/amd-strix-halo-toolboxes)
inside rootless Distrobox containers. It does not install ROCm, llama.cpp, or
model weights on the immutable system image.

The same `ujust strix-halo-ai` menu opens the separate stable/experimental
ComfyUI manager. See [Strix Halo ComfyUI](strix-halo-comfyui.md) for image and
video generation, persistent data, and update behavior.

This is separate from RamaLama. Use RamaLama for broader AMD hardware such as
Radeon 780M systems. The only shared convention is that persistent model files
live below `~/ai/models`.

## Setup menu

Run:

```bash
ujust strix-halo-ai
```

The menu installs, updates, verifies, or removes either llama.cpp backend,
downloads the recommended LLM GGUF models, opens a separate ComfyUI model
download submenu, and opens the ComfyUI manager. Its lifecycle operations are
idempotent. Install keeps
an existing container; Update/recreate intentionally replaces it from the
newest image for the same stable tag; Remove leaves all model files intact.

The stable choices, verified against upstream on 2026-08-29, are:

| Backend | Distrobox | Image |
| --- | --- | --- |
| Vulkan RADV | `strix-halo-vulkan` | `docker.io/kyuz0/amd-strix-halo-toolboxes:vulkan-radv` |
| ROCm | `strix-halo-rocm` | `docker.io/kyuz0/amd-strix-halo-toolboxes:rocm-10.0` |

Vulkan RADV is upstream's most compatible option. ROCm 10.0 is its current
stable ROCm Core SDK build for `gfx1151`. Experimental, performance, custom,
and nightly tags are intentionally excluded.

For automation or diagnosis, the recipe also accepts a subcommand:

```bash
ujust strix-halo-ai -- verify
ujust strix-halo-ai -- install vulkan
ujust strix-halo-ai -- update both
ujust strix-halo-ai -- remove rocm
ujust strix-halo-ai -- download-models
ujust strix-halo-ai -- stop both
ujust strix-halo-ai -- version both
```

`stop` defaults to both backends. It only terminates `llama-server` instances
running in router mode, so a directly launched single-model server is left
alone.

`version` also defaults to both backends and reports the installed toolbox
image together with each `llama-server` build version.

## Hardware and device checks

Mutating operations require all of these signals:

- AMD display PCI device `1002:1586`, the Strix Halo graphics controller;
- the `amdgpu` kernel driver bound to that device; and
- a Ryzen AI MAX CPU model.

The PCI ID is the primary stable identifier; the CPU family and driver avoid a
single fragile marketing-string check. Unsupported hardware stops with a
pointer to RamaLama. Developers can bypass only this gate with
`STRIX_HALO_AI_ALLOW_UNSUPPORTED=1`; device-access checks still apply.

Vulkan receives `/dev/dri`. ROCm receives `/dev/dri` and `/dev/kfd`. Both are
created with:

```text
--group-add keep-groups --security-opt seccomp=unconfined
```

`keep-groups` carries the host user's supplementary GIDs through rootless
Podman. Named `--group-add video --group-add render` values would instead be
resolved inside the container and can refer to different GIDs. The verifier
reports host membership in `render` and `video` as well as effective read/write
access. An ACL or device mode can grant access even when group membership is
absent. If access is missing, add the user to the host groups declaratively and
log out and back in; the setup never installs a `MODE=0666` udev rule.

The verifier reports the kernel and observable amdgpu GTT/VRAM totals but does
not modify BIOS settings, kernel arguments, the bootloader, firmware, or GTT.

## Host commands and defaults

Setup installs these commands in `~/.local/bin`:

```text
llama-vulkan             llama-cli in strix-halo-vulkan
llama-server-vulkan      llama-server in strix-halo-vulkan
llama-rocm               llama-cli in strix-halo-rocm
llama-server-rocm        llama-server in strix-halo-rocm
strix-vulkan-shell       interactive Vulkan Distrobox shell
strix-rocm-shell         interactive ROCm Distrobox shell
```

The llama wrappers add the current Strix Halo defaults only when the caller has
not supplied an equivalent option:

```text
--load-mode none -ngl 999 -fa 1
```

Kyuz0's current README still spells the first setting `--no-mmap`; the current
llama.cpp build accepts it but emits a deprecation warning and requests
`--load-mode none`. The wrapper uses that exact warning-free equivalent and
recognizes `--mmap`, `--no-mmap`, and `--load-mode` as caller overrides.

Server wrappers also default to `--host 127.0.0.1 --port 8080`. Explicit
options win, including their long aliases. Both `llama-server-vulkan` and
`llama-server-rocm` start in router mode by default with `--models-dir
~/ai/models`, so they list the downloaded `muse-glimmer-30b`,
`qwen3.6-35b-a3b`, and `qwen3.8-27b` model IDs and load the requested model on
demand. Router mode defaults to `--models-max 1`, so loading a second model
unloads the first and avoids keeping multiple large models resident. Supply
`--models-max N` to choose another limit. Supplying `-m`/`--model`, an HF
repository, `--models-dir`, or `--models-preset` retains direct control instead.

The two bundled Qwen models are MTP-capable. Direct Qwen launches default to
`--spec-type draft-mtp --spec-draft-n-max 3`; the managed router preset applies
the same settings to their router entries. This is deliberately not applied to
Muse Glimmer. An explicit `--spec-type` takes ownership of speculative-decoding
configuration.

For example, these are accepted without duplicate defaults:

```bash
llama-rocm --mmap --gpu-layers 80 --flash-attn off -m /path/to/model.gguf
llama-server-rocm --host 0.0.0.0 --port 9000 -m /path/to/model.gguf
llama-server-rocm --models-dir "$HOME/ai/models" --models-max 2
```

The localhost default avoids accidental LAN exposure. Binding `0.0.0.0` is an
intentional LAN exposure; review the firewall and access controls before doing
so. These Distroboxes use the host network namespace (the setup does not pass
`--unshare-netns`), so a server bound to localhost inside them is reachable
from the host at the same address.

For a plain-language guide to one-time launch options, persistent per-model
presets, MTP choices, client model IDs, and troubleshooting, see
[Configuring Strix Halo local AI](strix-halo-ai-configuration.md).

## Recommended models

The image manages Homebrew's bottled `hf` formula, which supplies the current
Hugging Face CLI. The downloader uses `hf download`, enables Xet's
high-performance path, and forwards an existing `HF_TOKEN`. Existing
deployments that have not rebased to an image containing that formula retain a
container-only fallback; nothing is installed into the host Python environment.
Hugging Face downloads are resumable. Complete files with both the verified
upstream byte size and matching Hugging Face Xet SHA-256 metadata are reused;
partial files resume. Before starting, the operation checks the remaining
payload size plus a 5 GiB safety margin.

The selected files are:

| Model directory | Artifacts |
| --- | --- |
| `~/ai/models/qwen3.6-35b-a3b/` | MTP variant of `Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf`, `mmproj-F16.gguf` |
| `~/ai/models/muse-glimmer-30b/` | `Muse-Glimmer-30B-UD-Q4_K_XL.gguf`, `mmproj-kquant.gguf` |
| `~/ai/models/qwen3.8-27b/` | `Qwen3.8-27B-UD-Q4_K_XL.gguf`, `mmproj-F16.gguf` |

Qwen 3.6 uses Unsloth's MTP GGUF repository so the wrapper's MTP default has
real model heads to use; it keeps the requested filename and destination but is
not byte-identical to the non-MTP repository variant. Qwen 3.8 already carries
MTP heads in its selected artifact. Qwen 3.6 and Qwen 3.8 currently publish
F16, BF16, and (for Qwen 3.6) F32 projectors. F16 is the compatible
inference-oriented choice without downloading larger redundant variants. Muse
Glimmer's upstream GGUF instructions identify the 1.4 GB k-quant projector as
the perception encoder required for image input; Unsloth mirrors that exact
artifact as `mmproj-kquant.gguf`. The Q8_0 and BF16 Muse projectors are
therefore not downloaded. Projectors are optional for text-only use and are
supplied to llama.cpp with `--mmproj` for images.

Because Distrobox shares the host home directory, each path is identical inside
both containers. No model bind mount exists, and deleting or recreating a
container cannot delete this directory.

Example text inference:

```bash
llama-vulkan \
  -m "$HOME/ai/models/qwen3.6-35b-a3b/Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf" \
  -p 'Reply with exactly: Vulkan works.' -n 16
```

Example multimodal server:

```bash
llama-server-rocm \
  -m "$HOME/ai/models/qwen3.8-27b/Qwen3.8-27B-UD-Q4_K_XL.gguf" \
  --mmproj "$HOME/ai/models/qwen3.8-27b/mmproj-F16.gguf"
```

## Pi Agent and OpenAI-compatible clients

Start either server wrapper with no model argument for the default router, then
configure Pi Agent's OpenAI-compatible provider with:

```text
Base URL: http://127.0.0.1:8080/v1
API key:  any non-empty placeholder if the client requires one
Model:    the identifier returned by GET /v1/models
```

For the downloaded bundles, the returned IDs are `muse-glimmer-30b`,
`qwen3.6-35b-a3b`, and `qwen3.8-27b`; the router loads a selected model on its
first request. For example:

```bash
llama-server-rocm # or llama-server-vulkan
curl -fsS http://127.0.0.1:8080/v1/models | jq -r '.data[] | [.id, .status.value] | @tsv'
```

Check the endpoint from the host:

```bash
curl -fsS http://127.0.0.1:8080/health
curl -fsS http://127.0.0.1:8080/v1/models | jq
curl -fsS http://127.0.0.1:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"MODEL_ID","messages":[{"role":"user","content":"Say hello."}]}'
```

If `/health` fails, first check whether anything is listening and which
container process is running:

```bash
ss -ltnp 'sport = :8080'
podman ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
```

No listening socket indicates a process/startup or model-loading failure, so
inspect the `llama-server` terminal. A healthy `/health` response with a client
failure indicates URL, model-ID, or client configuration instead. If the port
is busy, choose another one with `--port`; if the service is bound to
`127.0.0.1`, remote LAN clients cannot reach it by design.

## Manual verification and recovery

The menu's Verify/test operation reports hardware, permissions, dependencies,
container images, model visibility, wrappers, unified-memory sysfs values, and
`llama-cli --list-devices` from each installed backend. Useful manual commands:

```bash
ujust strix-halo-ai -- verify
podman inspect --format '{{.Config.Image}}' strix-halo-vulkan
podman inspect --format '{{.Config.Image}}' strix-halo-rocm
distrobox enter --name strix-halo-vulkan -- llama-cli --list-devices
distrobox enter --name strix-halo-rocm -- llama-cli --list-devices
ls -l /dev/dri /dev/kfd
id
```

If `/dev/dri` is absent, investigate amdgpu on the host. If `/dev/kfd` alone is
absent, ROCm cannot run even though Vulkan may work. If device nodes exist but
are inaccessible, fix host membership/ACLs and re-login, then recreate the
container so `keep-groups` captures the new supplementary groups. Do not solve
this with world-writable device rules.

Use the menu Update/recreate actions to pull a newer rebuild of the same stable
tag, replace only the selected Distrobox, rerun its GPU check, and refresh the
wrappers. Cleanup is limited to dangling images from
`docker.io/kyuz0/amd-strix-halo-toolboxes`; it never broadly prunes Podman.

Upstream resources:

- [AMD Strix Halo llama.cpp toolboxes](https://github.com/kyuz0/amd-strix-halo-toolboxes)
- [Qwen3.6 35B A3B MTP GGUF](https://huggingface.co/unsloth/Qwen3.6-35B-A3B-MTP-GGUF)
- [Muse Glimmer 30B GGUF](https://huggingface.co/unsloth/Muse-Glimmer-30B-GGUF)
- [Qwen3.8 27B GGUF](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF)
- [llama.cpp](https://github.com/ggml-org/llama.cpp)
