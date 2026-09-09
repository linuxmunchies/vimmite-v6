set shell := ["bash", "-euo", "pipefail", "-c"]
set positional-arguments

[doc('Open the guided Vimmite first-run setup menu')]
[group('Vimmite')]
vimmite-setup:
    /usr/libexec/vimmite-setup

[doc('Check image, graphics, gaming, containers, storage, and service health')]
[group('Vimmite')]
vimmite-doctor:
    /usr/libexec/vimmite-doctor

[doc('Create a private, redacted diagnostic archive in the current directory')]
[group('Vimmite')]
vimmite-support-bundle output="":
    #!/usr/bin/env bash
    /usr/libexec/vimmite-support-bundle "$@"

[doc('Build and manage the declarative vimmite-dev development Distrobox')]
[group('Development')]
vimmite-dev *args:
    /usr/libexec/vimmite-devbox "$@"

[doc('Manage stable Vulkan and ROCm llama.cpp Distroboxes for Strix Halo/gfx1151')]
[group('Strix Halo AI')]
strix-halo-ai *args:
    /usr/libexec/vimmite-strix-halo-ai "$@"

[doc('Install the image-baked Zim setup without overwriting shell configuration')]
[group('Vimmite')]
setup-zsh set_login_shell="false":
    #!/usr/bin/env bash
    set -euo pipefail

    user_name="$(id -un)"
    user_home="$(getent passwd "${user_name}" | cut -d: -f6)"
    template_dir="/usr/share/vimmite/zim"

    if [[ ! -d "${user_home}/.zim" ]]; then
        cp -a "${template_dir}/skel/.zim" "${user_home}/.zim"
        echo "Installed the image-baked Zim modules in ${user_home}/.zim"
    else
        echo "Keeping existing ${user_home}/.zim"
    fi

    if [[ ! -e "${user_home}/.zimrc" ]]; then
        install -m 0644 "${template_dir}/zimrc" "${user_home}/.zimrc"
        echo "Installed ${user_home}/.zimrc"
    else
        echo "Keeping existing ${user_home}/.zimrc"
    fi

    if [[ ! -e "${user_home}/.zshrc" ]]; then
        install -m 0644 "${template_dir}/zshrc" "${user_home}/.zshrc"
        echo "Installed ${user_home}/.zshrc"
    else
        echo "Keeping existing ${user_home}/.zshrc"
    fi

    ZIM_HOME="${user_home}/.zim" \
    ZIM_CONFIG_FILE="${user_home}/.zimrc" \
        zsh -c 'source /usr/share/vimmite/zim/zimfw.zsh init'

    if [[ "{{ set_login_shell }}" == "true" ]]; then
        sudo usermod --shell /usr/bin/zsh "${user_name}"
        echo "Zsh will be the login shell after the next login."
    else
        echo "Zim is ready. Run 'ujust setup-zsh true' to also select Zsh as the login shell."
    fi

[doc('Prepare the default network and verify system virtualization')]
[group('Vimmite')]
setup-virtualization:
    #!/usr/bin/env bash
    set -euo pipefail

    sockets=(
        virtqemud.socket
        virtnetworkd.socket
        virtstoraged.socket
        virtsecretd.socket
        virtnodedevd.socket
        virtnwfilterd.socket
    )

    sudo systemctl enable --now "${sockets[@]}"

    # The installer creates private home directories (0700). Grant only the
    # qemu service account directory traversal so libvirt can open ISO images
    # selected from ~/Downloads; this does not permit listing the home folder.
    if getent passwd qemu >/dev/null; then
        sudo setfacl --modify u:qemu:--x "${HOME}"
    fi

    if sudo virsh net-info default >/dev/null 2>&1; then
        sudo virsh net-autostart default
        if ! sudo virsh net-info default | grep -q '^Active:.*yes'; then
            sudo virsh net-start default
        fi
    else
        echo "The libvirt default network was not found." >&2
        exit 1
    fi

    virsh --connect qemu:///system uri
    echo "Virtualization is ready for this administrator account."

[doc('Opt into automatic mounting of labeled internal Btrfs and ext4 drives')]
[group('Vimmite')]
automount action="status":
    #!/usr/bin/env bash
    set -euo pipefail

    case "{{ action }}" in
        enable)
            sudo systemctl enable --now ublue-os-media-automount.service
            systemctl --no-pager --full status ublue-os-media-automount.service || true
            ;;
        disable)
            sudo systemctl disable --now ublue-os-media-automount.service
            echo "Automatic mounting is disabled. Existing transient mounts are left intact until reboot."
            ;;
        status)
            systemctl is-enabled ublue-os-media-automount.service || true
            systemctl is-active ublue-os-media-automount.service || true
            findmnt -rn -o TARGET,SOURCE,FSTYPE | grep '^/run/media/system/' || true
            ;;
        *)
            echo "Usage: ujust automount [status|enable|disable]" >&2
            exit 2
            ;;
    esac

[doc('Opt into the HyperX Cloud Alpha Wireless microphone-volume helper')]
[group('Vimmite')]
hyperx-mic action="status":
    #!/usr/bin/env bash
    set -euo pipefail

    unit="vimmite-hyperx-mic-volume.path"
    case "{{ action }}" in
        enable)
            echo "This enables a user path unit that sets a detected HyperX Cloud Alpha Wireless microphone to 90%."
            systemctl --user enable --now "${unit}"
            echo "HyperX microphone handling is enabled for this user."
            ;;
        disable)
            systemctl --user disable --now "${unit}"
            echo "HyperX microphone handling is disabled for this user."
            ;;
        status)
            systemctl --user is-enabled "${unit}" || true
            systemctl --user is-active "${unit}" || true
            ;;
        *)
            echo "Usage: ujust hyperx-mic [status|enable|disable]" >&2
            exit 2
            ;;
    esac

[doc('Install Moonlight, Sunshine, or both as optional user Flatpaks')]
[group('Vimmite')]
install-streaming component="moonlight":
    #!/usr/bin/env bash
    set -euo pipefail

    install_moonlight() {
        flatpak --user install --assumeyes --or-update flathub com.moonlight_stream.Moonlight
    }

    install_sunshine() {
        flatpak --user install --assumeyes --or-update flathub dev.lizardbyte.app.Sunshine
        flatpak run --command=additional-install.sh dev.lizardbyte.app.Sunshine
        echo "Sunshine's additional host integration completed. Reboot before testing capture and controller input."
    }

    case "{{ component }}" in
        moonlight)
            install_moonlight
            ;;
        sunshine)
            install_sunshine
            ;;
        both)
            install_moonlight
            install_sunshine
            ;;
        *)
            echo "Usage: ujust install-streaming [moonlight|sunshine|both]" >&2
            exit 2
            ;;
    esac

[doc('Enable, disable, or inspect the OpenSSH server and firewall rule')]
[group('Vimmite')]
ssh-server action="status":
    #!/usr/bin/env bash
    set -euo pipefail

    case "{{ action }}" in
        enable)
            sudo firewall-cmd --permanent --add-service=ssh
            sudo firewall-cmd --reload
            sudo systemctl enable --now sshd.service
            echo "SSH is enabled. Verify authentication before relying on remote access."
            ;;
        disable)
            sudo systemctl disable --now sshd.service
            if sudo firewall-cmd --permanent --query-service=ssh; then
                sudo firewall-cmd --permanent --remove-service=ssh
                sudo firewall-cmd --reload
            fi
            ;;
        status)
            systemctl is-enabled sshd.service || true
            systemctl is-active sshd.service || true
            firewall-cmd --query-service=ssh || true
            ;;
        *)
            echo "Usage: ujust ssh-server [status|enable|disable]" >&2
            exit 2
            ;;
    esac

[doc('Configure magic-packet Wake-on-LAN for a NetworkManager Ethernet connection')]
[group('Vimmite')]
wake-on-lan interface="" action="status":
    #!/usr/bin/env bash
    set -euo pipefail

    network_interface="{{ interface }}"
    if [[ -z "${network_interface}" ]]; then
        nmcli --fields DEVICE,TYPE,STATE,CONNECTION device status
        echo "Usage: ujust wake-on-lan <interface> [status|enable|disable]"
        exit 0
    fi

    if [[ "$(nmcli --get-values GENERAL.TYPE device show "${network_interface}")" != "ethernet" ]]; then
        echo "${network_interface} is not an Ethernet interface." >&2
        exit 1
    fi

    connection="$(nmcli --get-values GENERAL.CONNECTION device show "${network_interface}")"
    if [[ -z "${connection}" || "${connection}" == "--" ]]; then
        echo "${network_interface} has no active NetworkManager connection." >&2
        exit 1
    fi

    case "{{ action }}" in
        enable)
            if ! ethtool "${network_interface}" | grep -Eq 'Supports Wake-on:.*g'; then
                echo "${network_interface} does not report magic-packet Wake-on-LAN support." >&2
                exit 1
            fi
            sudo nmcli connection modify "${connection}" 802-3-ethernet.wake-on-lan magic
            echo "Wake-on-LAN is set to magic packets for '${connection}'. It applies after reconnect or reboot."
            ;;
        disable)
            sudo nmcli connection modify "${connection}" 802-3-ethernet.wake-on-lan default
            echo "Wake-on-LAN for '${connection}' is restored to NetworkManager's default."
            ;;
        status)
            nmcli --fields 802-3-ethernet.wake-on-lan connection show "${connection}"
            ethtool "${network_interface}" | grep -E 'Supports Wake-on:|Wake-on:' || true
            ;;
        *)
            echo "Usage: ujust wake-on-lan <interface> [status|enable|disable]" >&2
            exit 2
            ;;
    esac

[doc('Manage the legacy large-memory profile only on the GMKtec Ryzen AI MAX+ 395 host')]
[group('Vimmite')]
setup-ai-max action="status":
    #!/usr/bin/env bash
    set -euo pipefail

    cpu_model="$(sed -n 's/^model name[[:space:]]*: //p' /proc/cpuinfo | head -n1)"
    system_vendor="$(cat /sys/class/dmi/id/sys_vendor 2>/dev/null || true)"
    product_name="$(cat /sys/class/dmi/id/product_name 2>/dev/null || true)"
    expected_host=false

    if [[ "${cpu_model}" == *"AMD RYZEN AI MAX+ 395"* && "${system_vendor}" == "GMKtec" && "${product_name}" == "NucBox_EVO-X2" ]]; then
        expected_host=true
    fi

    case "{{ action }}" in
        status)
            echo "CPU: ${cpu_model}"
            echo "System: ${system_vendor} ${product_name}"
            echo "Recognized AI MAX host: ${expected_host}"
            rpm-ostree kargs
            ;;
        apply)
            if [[ "${expected_host}" != "true" ]]; then
                echo "Refusing to apply AI MAX kernel arguments on an unrecognized host." >&2
                exit 1
            fi
            echo "This enables AMD IOMMU and restores the large TTM/GTT values used for AI workloads."
            echo "The amdgpu.gttsize argument is deprecated upstream and remains a temporary compatibility setting."
            read -r -p "Create a new deployment with this legacy profile? [y/N] " answer
            if [[ ! "${answer}" =~ ^[Yy]$ ]]; then
                echo "No changes made."
                exit 0
            fi
            sudo rpm-ostree kargs \
                --delete-if-present=iommu=off \
                --append-if-missing=amd_iommu=on \
                --append-if-missing=ttm.pages_limit=30720000 \
                --append-if-missing=amdgpu.gttsize=122880
            echo "A reboot is required. IOMMU is no longer disabled."
            ;;
        undo)
            if [[ "${expected_host}" != "true" ]]; then
                echo "Refusing to alter AI MAX kernel arguments on an unrecognized host." >&2
                exit 1
            fi
            sudo rpm-ostree kargs \
                --delete-if-present=amd_iommu=on \
                --delete-if-present=ttm.pages_limit=30720000 \
                --delete-if-present=amdgpu.gttsize=122880
            echo "The AI MAX profile is removed from the next deployment. A reboot is required."
            ;;
        *)
            echo "Usage: ujust setup-ai-max [status|apply|undo]" >&2
            exit 2
            ;;
    esac

# RamaLama is installed per user so it works on the immutable image without
# layering packages or changing the host configuration.
ramalama_store := env_var_or_default("RAMALAMA_STORE", env_var("HOME") + "/ai/models")
ramalama_cli_dir := env_var_or_default("RAMALAMA_CLI_DIR", env_var("HOME") + "/.local/share/ramalama-cli")
ramalama_bin := env_var_or_default("RAMALAMA_BIN", ramalama_cli_dir + "/bin/ramalama")
ramalama_user_bin_dir := env_var_or_default("RAMALAMA_USER_BIN_DIR", env_var("HOME") + "/.local/bin")
ramalama_backend := env_var_or_default("RAMALAMA_BACKEND", "vulkan")
ramalama_ngl := env_var_or_default("RAMALAMA_NGL", "auto")
ramalama_context_tokens := env_var_or_default("RAMALAMA_CONTEXT", "4096")

# Each Hugging Face transport selects exactly one GGUF quantization.
ramalama_qwen := "hf://unsloth/Qwen3.5-35B-A3B-GGUF:UD-Q4_K_XL"
ramalama_ornith := "hf://ornith-ai/Ornith-1.5-9B-GGUF:Q4_K_M"
ramalama_gemma := "hf://unsloth/gemma-4-26B-A4B-it-GGUF:UD-Q4_K_XL"
ramalama_laguna := "hf://ggml-org/Laguna-XS-2.1-GGUF:Q4_K_M"
ramalama_granite := "hf://bartowski/granite-4.2-8b-GGUF:Q4_K_M"
ramalama_nemotron := "hf://unsloth/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-GGUF:UD-Q4_K_XL"
ramalama_liquid := "hf://LiquidAI/LFM2.5-8B-A1B-GGUF:Q4_K_M"
ramalama_north := "hf://unsloth/North-Mini-Code-1.0-GGUF:UD-Q4_K_M"

[private]
_ramalama-require:
    #!/usr/bin/env bash
    if [[ ! -x "{{ ramalama_bin }}" ]]; then
        echo "RamaLama is not installed in {{ ramalama_cli_dir }}." >&2
        echo "Run: ujust ramalama-setup" >&2
        exit 1
    fi

[private]
_ramalama-check-all-space:
    #!/usr/bin/env bash
    # The requested GGUF payloads total about 120 GiB before optional
    # projectors, OCI images, and metadata. Retain a modest safety margin.
    probe="{{ ramalama_store }}"
    while [[ ! -e "${probe}" ]]; do
        probe="$(dirname "${probe}")"
    done
    available_kib="$(df -Pk "${probe}" | awk 'NR == 2 { print $4 }')"
    minimum_kib=$((145 * 1024 * 1024))
    if (( available_kib < minimum_kib )); then
        available_gib=$((available_kib / 1024 / 1024))
        echo "Need at least 145 GiB free for ramalama-pull-all; only ${available_gib} GiB is free." >&2
        echo "Set RAMALAMA_STORE to a larger filesystem, or pull individual models." >&2
        exit 1
    fi

[doc('Check the non-destructive prerequisites for AMD Vulkan inference')]
[group('RamaLama')]
ramalama-preflight:
    #!/usr/bin/env bash
    set -euo pipefail

    command -v podman >/dev/null || { echo "Podman is required." >&2; exit 1; }
    command -v python3 >/dev/null || { echo "python3 is required." >&2; exit 1; }
    command -v jq >/dev/null || { echo "jq is required." >&2; exit 1; }

    echo "Podman rootless: $(podman info --format json | jq -r '.host.security.rootless')"
    if [[ -r /dev/dri/renderD128 ]]; then
        echo "DRM render node: readable (/dev/dri/renderD128)"
    else
        echo "WARNING: /dev/dri/renderD128 is not readable; Vulkan container access may fail." >&2
    fi

    if command -v vulkaninfo >/dev/null; then
        vulkan_summary="$(vulkaninfo --summary 2>&1 || true)"
        if grep -Eqi 'AMD.*Radeon|Radeon.*AMD' <<<"${vulkan_summary}"; then
            echo "Vulkan: AMD device detected"
        else
            echo "WARNING: vulkaninfo did not report an AMD Radeon device." >&2
        fi
    else
        echo "WARNING: vulkaninfo is unavailable; install the Vulkan tools only if you need this diagnostic." >&2
    fi

    available_mem_kib="$(awk '/MemAvailable:/ { print $2 }' /proc/meminfo)"
    available_mem_gib=$((available_mem_kib / 1024 / 1024))
    echo "Available RAM: ${available_mem_gib} GiB"
    echo "Model store: {{ ramalama_store }}"
    echo "Backend: {{ ramalama_backend }}; GPU layers: {{ ramalama_ngl }}; context: {{ ramalama_context_tokens }}"

[doc('Install/update RamaLama and Hugging Face CLI without downloading models')]
[group('RamaLama')]
ramalama-install:
    #!/usr/bin/env bash
    set -euo pipefail

    if [[ ! -x "{{ ramalama_cli_dir }}/bin/python" ]]; then
        python3 -m venv "{{ ramalama_cli_dir }}"
    fi
    "{{ ramalama_cli_dir }}/bin/python" -m pip install --upgrade pip
    "{{ ramalama_cli_dir }}/bin/python" -m pip install --upgrade ramalama 'huggingface_hub[cli]'

    # Keep the executable at a conventional user-local path. The symlink is
    # updated on every install/update, so it follows future upgrades.
    mkdir -p "{{ ramalama_user_bin_dir }}"
    ln -sfn "{{ ramalama_bin }}" "{{ ramalama_user_bin_dir }}/ramalama"

    # ujust cannot alter its caller's environment. Ensure new Zsh terminals
    # find the standard user-local bin directory.
    zshrc="${HOME}/.zshrc"
    path_line='export PATH="$HOME/.local/bin:$PATH"'
    if ! [[ -f "${zshrc}" ]] || ! grep -Fqx "${path_line}" "${zshrc}"; then
        {
            echo
            echo '# RamaLama command path (managed by Vimmite)'
            echo "${path_line}"
        } >> "${zshrc}"
        echo "Added ~/.local/bin to ${zshrc}; open a new terminal to use 'ramalama'."
    fi

    "{{ ramalama_bin }}" version
    echo "Installed without sudo. 'ramalama' is available at {{ ramalama_user_bin_dir }}/ramalama."
    echo "Models will be stored in: {{ ramalama_store }}"

[doc('Set up RamaLama only: install the CLI and do not download any model')]
[group('RamaLama')]
ramalama-setup: ramalama-preflight ramalama-install
    @echo "RamaLama is ready without models. Run an individual ramalama-pull-* recipe when wanted."

[doc('List models already present in the configured RamaLama model store')]
[group('RamaLama')]
ramalama-list: _ramalama-require
    "{{ ramalama_bin }}" --store "{{ ramalama_store }}" list

[doc('Download Qwen3.5 35B-A3B, Unsloth Dynamic Q4_K_XL')]
[group('RamaLama pulls')]
ramalama-pull-qwen: _ramalama-require
    "{{ ramalama_bin }}" --store "{{ ramalama_store }}" pull "{{ ramalama_qwen }}"

[doc('Download Ornith 1.5 9B, Q4_K_M')]
[group('RamaLama pulls')]
ramalama-pull-ornith: _ramalama-require
    "{{ ramalama_bin }}" --store "{{ ramalama_store }}" pull "{{ ramalama_ornith }}"

[doc('Download Gemma 4 26B-A4B, Unsloth Dynamic Q4_K_XL')]
[group('RamaLama pulls')]
ramalama-pull-gemma: _ramalama-require
    "{{ ramalama_bin }}" --store "{{ ramalama_store }}" pull "{{ ramalama_gemma }}"

[doc('Download Laguna XS 2.1, Q4_K_M')]
[group('RamaLama pulls')]
ramalama-pull-laguna: _ramalama-require
    "{{ ramalama_bin }}" --store "{{ ramalama_store }}" pull "{{ ramalama_laguna }}"

[doc('Download Granite 4.2 8B, Q4_K_M')]
[group('RamaLama pulls')]
ramalama-pull-granite: _ramalama-require
    "{{ ramalama_bin }}" --store "{{ ramalama_store }}" pull "{{ ramalama_granite }}"

[doc('Download NVIDIA Nemotron 3.5 Lightning 30B-A3B, Unsloth Dynamic Q4_K_XL')]
[group('RamaLama pulls')]
ramalama-pull-nemotron: _ramalama-require
    "{{ ramalama_bin }}" --store "{{ ramalama_store }}" pull "{{ ramalama_nemotron }}"

[doc('Download Liquid LFM2.5 8B-A1B, Q4_K_M')]
[group('RamaLama pulls')]
ramalama-pull-liquid: _ramalama-require
    "{{ ramalama_bin }}" --store "{{ ramalama_store }}" pull "{{ ramalama_liquid }}"

[doc('Download Cohere North Mini Code 1.0, Unsloth Dynamic Q4_K_M')]
[group('RamaLama pulls')]
ramalama-pull-north: _ramalama-require
    "{{ ramalama_bin }}" --store "{{ ramalama_store }}" pull "{{ ramalama_north }}"

[doc('Download every requested model after confirming a 145 GiB free-space safety margin')]
[group('RamaLama pulls')]
ramalama-pull-all: _ramalama-check-all-space ramalama-pull-qwen ramalama-pull-ornith ramalama-pull-gemma ramalama-pull-laguna ramalama-pull-granite ramalama-pull-nemotron ramalama-pull-liquid ramalama-pull-north
    @echo "All requested pulls finished. Use ramalama-list to review the local store."

[doc('Set up RamaLama and download every requested model (at least 145 GiB free)')]
[group('RamaLama')]
ramalama-setup-all: ramalama-preflight ramalama-install ramalama-pull-all
    @echo "RamaLama and all requested models are ready. Run ramalama-smoke next."

[doc('Run a short real Vulkan smoke test after confirming the Liquid model is already local')]
[group('RamaLama')]
ramalama-smoke: _ramalama-require
    #!/usr/bin/env bash
    set -euo pipefail

    echo "This checks the Vulkan container path with a 2K context and 24 generated tokens."
    echo "It requires ramalama-pull-liquid to have completed first."
    command -v jq >/dev/null || { echo "jq is required for the local-model check." >&2; exit 1; }
    if ! "{{ ramalama_bin }}" --store "{{ ramalama_store }}" list --json | jq -e --arg repo "LiquidAI/LFM2.5-8B-A1B-GGUF" --arg tag "Q4_K_M" 'any(.[]; (.name | contains($repo)) and (.name | ascii_upcase | contains($tag)))' >/dev/null; then
        echo "The Liquid Q4_K_M model is not fully local. Run ramalama-pull-liquid first." >&2
        exit 1
    fi
    RAMALAMA_CONTAINER_ENGINE=podman "{{ ramalama_bin }}" --store "{{ ramalama_store }}" run --backend "{{ ramalama_backend }}" --ngl "{{ ramalama_ngl }}" --runtime-args="-c 2048 -n 24" "{{ ramalama_liquid }}" "Reply with exactly: Vulkan works."

[doc('Run Qwen3.5 35B-A3B on Vulkan; an optional prompt follows the recipe name')]
[group('RamaLama runs')]
ramalama-run-qwen *prompt: _ramalama-require
    RAMALAMA_CONTAINER_ENGINE=podman "{{ ramalama_bin }}" --store "{{ ramalama_store }}" run --backend "{{ ramalama_backend }}" --ngl "{{ ramalama_ngl }}" --runtime-args="-c {{ ramalama_context_tokens }}" "{{ ramalama_qwen }}" "$@"

[doc('Run Ornith 1.5 on Vulkan; an optional prompt follows the recipe name')]
[group('RamaLama runs')]
ramalama-run-ornith *prompt: _ramalama-require
    RAMALAMA_CONTAINER_ENGINE=podman "{{ ramalama_bin }}" --store "{{ ramalama_store }}" run --backend "{{ ramalama_backend }}" --ngl "{{ ramalama_ngl }}" --runtime-args="-c {{ ramalama_context_tokens }}" "{{ ramalama_ornith }}" "$@"

[doc('Run Gemma 4 26B-A4B on Vulkan; an optional prompt follows the recipe name')]
[group('RamaLama runs')]
ramalama-run-gemma *prompt: _ramalama-require
    RAMALAMA_CONTAINER_ENGINE=podman "{{ ramalama_bin }}" --store "{{ ramalama_store }}" run --backend "{{ ramalama_backend }}" --ngl "{{ ramalama_ngl }}" --runtime-args="-c {{ ramalama_context_tokens }}" "{{ ramalama_gemma }}" "$@"

[doc('Run Laguna XS 2.1 on Vulkan; an optional prompt follows the recipe name')]
[group('RamaLama runs')]
ramalama-run-laguna *prompt: _ramalama-require
    RAMALAMA_CONTAINER_ENGINE=podman "{{ ramalama_bin }}" --store "{{ ramalama_store }}" run --backend "{{ ramalama_backend }}" --ngl "{{ ramalama_ngl }}" --runtime-args="-c {{ ramalama_context_tokens }}" "{{ ramalama_laguna }}" "$@"

[doc('Run Granite 4.2 8B on Vulkan; an optional prompt follows the recipe name')]
[group('RamaLama runs')]
ramalama-run-granite *prompt: _ramalama-require
    RAMALAMA_CONTAINER_ENGINE=podman "{{ ramalama_bin }}" --store "{{ ramalama_store }}" run --backend "{{ ramalama_backend }}" --ngl "{{ ramalama_ngl }}" --runtime-args="-c {{ ramalama_context_tokens }}" "{{ ramalama_granite }}" "$@"

[doc('Run Nemotron 3.5 Lightning on Vulkan; an optional prompt follows the recipe name')]
[group('RamaLama runs')]
ramalama-run-nemotron *prompt: _ramalama-require
    RAMALAMA_CONTAINER_ENGINE=podman "{{ ramalama_bin }}" --store "{{ ramalama_store }}" run --backend "{{ ramalama_backend }}" --ngl "{{ ramalama_ngl }}" --runtime-args="-c {{ ramalama_context_tokens }}" "{{ ramalama_nemotron }}" "$@"

[doc('Run Liquid LFM2.5 8B-A1B on Vulkan; an optional prompt follows the recipe name')]
[group('RamaLama runs')]
ramalama-run-liquid *prompt: _ramalama-require
    RAMALAMA_CONTAINER_ENGINE=podman "{{ ramalama_bin }}" --store "{{ ramalama_store }}" run --backend "{{ ramalama_backend }}" --ngl "{{ ramalama_ngl }}" --runtime-args="-c {{ ramalama_context_tokens }}" "{{ ramalama_liquid }}" "$@"

[doc('Run Cohere North Mini Code 1.0 on Vulkan; an optional prompt follows the recipe name')]
[group('RamaLama runs')]
ramalama-run-north *prompt: _ramalama-require
    RAMALAMA_CONTAINER_ENGINE=podman "{{ ramalama_bin }}" --store "{{ ramalama_store }}" run --backend "{{ ramalama_backend }}" --ngl "{{ ramalama_ngl }}" --runtime-args="-c {{ ramalama_context_tokens }}" "{{ ramalama_north }}" "$@"
