# Strix Halo ComfyUI

Vimmite provides two disposable, rootless ComfyUI Distroboxes for AMD Ryzen AI
MAX "Strix Halo" APUs (`gfx1151`). Vimmite manages lifecycle, GPU access, and
persistent paths; the upstream
[kyuz0 ComfyUI toolbox](https://github.com/kyuz0/amd-strix-halo-comfyui-toolboxes)
provides ROCm, TheRock PyTorch, ComfyUI, tuned launch settings, workflows,
custom nodes, and model-download helpers. None of that software is installed on
the immutable host.

## Open the manager

Run the main Strix Halo AI menu and choose **Manage ComfyUI image generation**:

```bash
ujust strix-halo-ai
```

The same manager also has a direct entry point:

```bash
ujust strix-halo-comfyui
```

Choose **Stable** for normal use or **Experimental** to try upstream's current
development build. Installation creates no models and does not start a service.

| Environment | Distrobox | Upstream image |
| --- | --- | --- |
| Stable (recommended) | `strix-halo-comfyui-stable` | `docker.io/kyuz0/amd-strix-halo-comfyui:latest` |
| Experimental | `strix-halo-comfyui-experimental` | `docker.io/kyuz0/amd-strix-halo-comfyui:dev` |

Upstream describes `latest` as its verified stable snapshot and `dev` as newer
workflows and dependencies that may be unstable. Both are currently built from
the same Fedora Rawhide Dockerfile with prerelease PyTorch packages from AMD's
TheRock multi-architecture nightly channel, scoped to `device-gfx1151`.
Upstream does not currently pin or document a ROCm major version for `dev`, so
Vimmite does not label it "ROCm 10." Diagnostics report the versions actually
installed in each container.

## Launch and models

From an environment's menu, choose **Launch locally**. Vimmite invokes the
upstream `start_comfy_ui` launcher, which currently supplies the changing Strix
Halo memory and VAE workarounds. Vimmite adds only persistent input and user-data
paths. Open:

```text
http://127.0.0.1:8000
```

The launcher does not pass `--listen`, so ComfyUI is not exposed to the LAN.
Advanced users can choose **Enter shell** to inspect the stack or run ComfyUI
manually. Binding it to a non-loopback address exposes an unauthenticated web
application unless the user adds suitable network and access controls.

Choose **Open Model Manager** to run upstream's `model_manager`. Downloads are
explicit and go to the shared model tree; installing or launching an environment
never downloads a large model automatically.

Direct commands are also available:

```bash
ujust strix-halo-comfyui -- install stable
ujust strix-halo-comfyui -- launch stable
ujust strix-halo-comfyui -- models stable
ujust strix-halo-comfyui -- shell experimental
ujust strix-halo-comfyui -- status both
ujust strix-halo-comfyui -- diagnostics
```

## Persistent data

Distrobox shares the host home directory. Vimmite prepares these paths:

| Path | Purpose | Shared between channels? |
| --- | --- | --- |
| `~/comfy-models` | Checkpoints, text encoders, VAEs, diffusion models, UNets, LoRAs, and vision models | Yes |
| `~/comfy-inputs` | User inputs and uploads | Yes |
| `~/comfy-outputs` | Generated images and videos | Yes |
| `~/comfy-user/stable` | Stable workflows, settings, and user database | No |
| `~/comfy-user/experimental` | Experimental workflows, settings, and user database | No |

Separating the two user directories prevents an experimental UI or database
change from overwriting stable settings. Vimmite seeds upstream's bundled UI
workflows into each user directory without overwriting an existing file.
Upstream's API workflow copies remain available inside the container at
`/opt/comfy-workflows`.

The upstream `/opt/set_extra_paths.sh` remains the source of truth for the model
folder mapping. Vimmite reruns it after every creation or refresh because the
generated configuration lives in the disposable `/opt/ComfyUI` tree.

## Updates, removal, and recovery

Normal launch reuses the existing Distrobox. It does not pull an image or change
channels behind the user's back.

**Update/refresh** is explicit and requires confirmation. It:

1. checks Strix Halo hardware and device access;
2. pulls the current image for only the selected channel;
3. deletes and recreates only that environment's Distrobox with the same
   rootless GPU options;
4. reruns upstream persistent-path setup and seeds any newly named bundled
   workflows;
5. checks PyTorch GPU visibility; and
6. removes only dangling image layers from this ComfyUI image repository.

The pull happens before deletion, so a failed download leaves the installed
container intact. The previous image ID is retained during recreation; if the
new container fails creation, persistent-path setup, or the GPU sanity check,
Vimmite attempts to restore the prior container automatically. A successful
refresh loses packages, custom nodes, edits, or other files stored only in
`/opt`, `/usr`, or elsewhere in the container filesystem. All paths in the
table above remain untouched.

**Remove container** also requires confirmation and removes only the selected
Distrobox. It does not delete models, inputs, outputs, workflows, or settings.
Install/create is idempotent: if the container exists it is left intact and its
persistent path setup and GPU check are rerun.

For intentional noninteractive automation, confirmation can be supplied with
`STRIX_HALO_COMFYUI_ASSUME_YES=1`. Review the target carefully before using it.

## GPU access and diagnostics

ComfyUI needs both `/dev/dri` and `/dev/kfd`. Vimmite reuses the same Strix Halo
hardware detection and effective device-access checks as its llama.cpp manager.
The rootless container receives:

```text
--device /dev/dri
--device /dev/kfd
--group-add keep-groups
--security-opt seccomp=unconfined
```

`keep-groups` preserves the host user's supplementary numeric GIDs, avoiding an
assumption that the container's `video` and `render` names have identical IDs.
No `sudo podman`, privileged container, world-writable device rule, SELinux
policy change, kernel argument, or host ROCm installation is added.

Diagnostics report the backing tag, running state, PyTorch version, HIP version,
ROCm SDK package version when present, `torch.cuda.is_available()`, GPU name and
architecture, and ComfyUI git revision. A developer can bypass only the hardware
identity gate with `STRIX_HALO_AI_ALLOW_UNSUPPORTED=1`; real `/dev/dri` and
`/dev/kfd` access is still required.

## Custom nodes

Upstream bundles its supported custom nodes below `/opt/ComfyUI/custom_nodes`.
Vimmite intentionally does not mount over that directory, because doing so would
hide the tested nodes in the image. Custom nodes or Python packages installed
manually inside the container are therefore lost on refresh. Keep a record of
manual additions and reinstall them after an update, or wait for an upstream
supported persistence mechanism rather than relying on container-local state.

See upstream for current workflows, model requirements, launch workarounds, and
container contents:

- [ComfyUI toolbox README](https://github.com/kyuz0/amd-strix-halo-comfyui-toolboxes)
- [Current Dockerfile](https://github.com/kyuz0/amd-strix-halo-comfyui-toolboxes/blob/main/Dockerfile)
- [Current refresh script](https://github.com/kyuz0/amd-strix-halo-comfyui-toolboxes/blob/main/refresh-toolbox.sh)
- [AI Toolbox Cockpit](https://github.com/kyuz0/ai-toolbox-cockpit)
