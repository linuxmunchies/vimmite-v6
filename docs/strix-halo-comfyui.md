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
Halo memory and VAE workarounds. Vimmite adds persistent model, input, and
user-data paths. Open:

```text
http://127.0.0.1:8000
```

The launcher does not pass `--listen`, so ComfyUI is not exposed to the LAN.
Advanced users can choose **Enter shell** to inspect the stack or run ComfyUI
manually. Binding it to a non-loopback address exposes an unauthenticated web
application unless the user adds suitable network and access controls.

Choose **Manage models (download / upload / status)** for Vimmite's curated
model menu. The header is a short color summary plus live percents for any active
downloads. Escape or Back leaves the menu; those jobs keep running. Each choice
starts with two columns, `disk=` (this PC) and `NAS=` (foxraid), each `yes`,
`2/3`, `no`, or `?` until you scan. The first visit offers a NAS scan; you
can run **Scan NAS** again later. Image generation lists **Qwen Image 2.1**
in BF16 and INT8, followed by **Krea 2 Turbo**. Hugging Face, NAS, and upload jobs run in the
background so you can queue another model without waiting; **Downloads** shows
logs and can stop a job. **Full status list** prints the complete table. NAS
transfers use
`//foxraid.local/ai/comfy-models` and keep the same destination layout;
required files are checked before copying and file sizes are verified after
the transfer. Uploads skip files that are not local. Required dependencies are
included with the corresponding bundle where the manifest specifies them, and
GLM-Image remains a Diffusers directory rather than being flattened. **Open
Model Manager** still runs upstream's `model_manager` for other explicit
downloads. Installing or launching an environment never downloads a large model
automatically.

Direct commands are also available:

```bash
ujust strix-halo-comfyui -- install stable
ujust strix-halo-comfyui -- check both
ujust strix-halo-comfyui -- update both
ujust strix-halo-comfyui -- refresh stable
ujust strix-halo-comfyui -- qwen21 both
ujust strix-halo-comfyui -- launch stable
ujust strix-halo-comfyui -- models stable
ujust strix-halo-comfyui -- download-models
ujust strix-halo-comfyui -- list-models
ujust strix-halo-comfyui -- model-status qwen-image-21
ujust strix-halo-comfyui -- model-status qwen-image-21-int8
ujust strix-halo-comfyui -- download-model qwen-image
ujust strix-halo-comfyui -- download-model-nas qwen-gguf
ujust strix-halo-comfyui -- upload-model krea-turbo
ujust strix-halo-comfyui -- upload-models
ujust strix-halo-comfyui -- download-jobs
ujust strix-halo-comfyui -- scan-nas
ujust strix-halo-comfyui -- shell experimental
ujust strix-halo-comfyui -- status both
ujust strix-halo-comfyui -- diagnostics
```

### Qwen Image 2.1 in both channels

Run `ujust strix-halo-comfyui -- qwen21 both` once after installing both
containers. This installs ComfyUI v0.37.0, the first official release with
native Qwen Image 2.1 nodes, when the upstream toolbox image is older. The
toolbox's ROCm PyTorch, torchvision, and torchaudio versions stay pinned during
this update. A marker in each persistent user directory restores Qwen support
after future container recreation; a newer upstream image with the required
nodes is used as supplied.

The command also adds three BF16 workflows (text to image, image edit, and
background removal) to each channel's **Workflows** list. They use the BF16
diffusion model and text encoder from `qwen-image-21`, plus its VAE. Both
channels share the same model folder, so one download serves both. The official
Template Library workflows default to INT8; download
`qwen-image-21-int8` to use those without changing their model selectors.
Existing user workflows are never overwritten. Restart a running ComfyUI
server after enabling Qwen support so it loads the new nodes.

## Persistent data

Distrobox shares the host home directory. Vimmite prepares these paths:

| Path | Purpose | Shared between channels? |
| --- | --- | --- |
| `~/ai/comfy-models` | Checkpoints, text encoders, VAEs, diffusion models, UNets, LoRAs, and vision models | Yes |
| `~/ai/comfy-inputs` | User inputs and uploads | Yes |
| `~/ai/comfy-outputs` | Generated images and videos | Yes |
| `~/ai/comfy-user/stable` | Stable workflows, settings, and user database | No |
| `~/ai/comfy-user/experimental` | Experimental workflows, settings, and user database | No |

Setup migrates leftover `~/comfy-inputs`, `~/comfy-outputs`, `~/comfy-user`, and
`~/comfy-models` into those `~/ai` destinations when present. A leftover tree is
moved when the destination is missing or empty, and a compatibility symlink is
left at the old path so an older image still finds the data. If both trees have
content, they are merged and the old tree is left in place. The live model root
is always `~/ai/comfy-models`.

The model downloader uses `HF_XET_HIGH_PERFORMANCE=1 hf download` and stores
files under the destination subdirectories listed in the model menu. Existing
complete files are reused when possible, while incomplete downloads can resume.
The NAS source uses the same destination layout, and **Upload to NAS** copies
local catalog files back to that share. Defaults are
`COMFYUI_NAS_HOST=foxraid.local`, `COMFYUI_NAS_SHARE=ai`,
`COMFYUI_NAS_SUBDIR=comfy-models`, and `COMFYUI_NAS_USER=guest`; set
`COMFYUI_NAS_PASSWORD` for a password-protected share. These variables can be
used with the direct command when the NAS is at a different location.

Separating the two user directories prevents an experimental UI or database
change from overwriting stable settings. Vimmite seeds upstream's bundled UI
workflows into each user directory without overwriting an existing file.
Upstream's API workflow copies remain available inside the container at
`/opt/comfy-workflows`.

Vimmite writes the model folder mapping to the disposable
`/opt/ComfyUI/extra_model_paths.yaml` after every creation or refresh, keeping
the shared model tree at `~/ai/comfy-models`. The upstream path helper is still
checked for compatibility with the selected image.

## Updates, removal, and recovery

Normal launch reuses the existing Distrobox. It does not pull an image or change
channels behind the user's back.

**Check** pulls the selected channel's current image and reports whether its
image ID differs from the installed container, without recreating it. **Update**
uses the same comparison and then:

1. checks Strix Halo hardware and device access;
2. pulls the current image for only the selected channel;
3. compares its image ID with the installed container and stops if they match;
4. if the image changed, asks for confirmation, then recreates that Distrobox with the same
   rootless GPU options;
5. reruns upstream persistent-path setup and seeds any newly named bundled
   workflows;
6. restores enabled Qwen Image 2.1 support, checks PyTorch GPU visibility; and
7. removes only dangling image layers from this ComfyUI image repository.

`ujust strix-halo-comfyui -- refresh stable` intentionally recreates a
container even when its image has not changed. It uses the same confirmation
and rollback path.

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
hide the tested nodes in the image. Create, update, and first launch install
ComfyUI-Manager with `pip install -U --pre comfyui-manager` in the container
venv and enable it with `--enable-manager`, because that package lives in the
disposable image. Other custom nodes or Python packages installed manually
inside the container are lost on refresh. Keep a record of those additions and
reinstall them after an update, or wait for an upstream supported persistence
mechanism rather than relying on container-local state.

See upstream for current workflows, model requirements, launch workarounds, and
container contents:

- [ComfyUI toolbox README](https://github.com/kyuz0/amd-strix-halo-comfyui-toolboxes)
- [Current Dockerfile](https://github.com/kyuz0/amd-strix-halo-comfyui-toolboxes/blob/main/Dockerfile)
- [Current refresh script](https://github.com/kyuz0/amd-strix-halo-comfyui-toolboxes/blob/main/refresh-toolbox.sh)
- [AI Toolbox Cockpit](https://github.com/kyuz0/ai-toolbox-cockpit)
