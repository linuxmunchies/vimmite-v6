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
    /usr/libexec/vimmite-setup-zsh "$@"

[doc('Prepare the default network and verify system virtualization')]
[group('Vimmite')]
setup-virtualization:
    /usr/libexec/vimmite-setup-virtualization "$@"

[doc('Opt into automatic mounting of labeled internal Btrfs and ext4 drives')]
[group('Vimmite')]
automount action="status":
    #!/usr/bin/env bash
    set -euo pipefail

    case "${1:-status}" in
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
    case "${1:-status}" in
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

    case "${1:-moonlight}" in
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

    case "${1:-status}" in
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
    /usr/libexec/vimmite-wake-on-lan "$@"

[doc('Manage the legacy large-memory profile only on the GMKtec Ryzen AI MAX+ 395 host')]
[group('Vimmite')]
setup-ai-max action="status":
    /usr/libexec/vimmite-setup-ai-max "$@"

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
    /usr/libexec/vimmite-ramalama-check-space "{{ ramalama_store }}"

[doc('Check the non-destructive prerequisites for AMD Vulkan inference')]
[group('RamaLama')]
ramalama-preflight:
    /usr/libexec/vimmite-ramalama-preflight "{{ ramalama_store }}" "{{ ramalama_backend }}" "{{ ramalama_ngl }}" "{{ ramalama_context_tokens }}"

[doc('Install/update RamaLama and Hugging Face CLI without downloading models')]
[group('RamaLama')]
ramalama-install:
    /usr/libexec/vimmite-ramalama-install "{{ ramalama_cli_dir }}" "{{ ramalama_user_bin_dir }}" "{{ ramalama_bin }}" "{{ ramalama_store }}"

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
    /usr/libexec/vimmite-ramalama-smoke "{{ ramalama_bin }}" "{{ ramalama_store }}" "{{ ramalama_backend }}" "{{ ramalama_ngl }}" "{{ ramalama_liquid }}"

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
