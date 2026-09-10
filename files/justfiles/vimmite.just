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

# RamaLama is installed per user. The public command is `ujust ramalama`;
# older recipe names remain as private aliases so existing scripts keep working.
[doc('Manage RamaLama: setup, pull from Hugging Face or the NAS, list, and run')]
[group('RamaLama')]
ramalama *args:
    /usr/libexec/vimmite-ramalama "$@"

[private]
ramalama-preflight:
    /usr/libexec/vimmite-ramalama preflight

[private]
ramalama-install:
    /usr/libexec/vimmite-ramalama setup

[private]
ramalama-setup:
    /usr/libexec/vimmite-ramalama setup

[private]
ramalama-list:
    /usr/libexec/vimmite-ramalama list

[private]
ramalama-pull-qwen:
    /usr/libexec/vimmite-ramalama pull hf qwen

[private]
ramalama-pull-ornith:
    /usr/libexec/vimmite-ramalama pull hf ornith

[private]
ramalama-pull-gemma:
    /usr/libexec/vimmite-ramalama pull hf gemma

[private]
ramalama-pull-laguna:
    /usr/libexec/vimmite-ramalama pull hf laguna

[private]
ramalama-pull-granite:
    /usr/libexec/vimmite-ramalama pull hf granite

[private]
ramalama-pull-nemotron:
    /usr/libexec/vimmite-ramalama pull hf nemotron

[private]
ramalama-pull-liquid:
    /usr/libexec/vimmite-ramalama pull hf liquid

[private]
ramalama-pull-north:
    /usr/libexec/vimmite-ramalama pull hf north

[private]
ramalama-pull-all:
    /usr/libexec/vimmite-ramalama pull hf all

[private]
ramalama-setup-all:
    #!/usr/bin/env bash
    /usr/libexec/vimmite-ramalama setup
    /usr/libexec/vimmite-ramalama pull hf all

[private]
ramalama-smoke:
    /usr/libexec/vimmite-ramalama smoke

[private]
ramalama-run-qwen *prompt:
    /usr/libexec/vimmite-ramalama run qwen "$@"

[private]
ramalama-run-ornith *prompt:
    /usr/libexec/vimmite-ramalama run ornith "$@"

[private]
ramalama-run-gemma *prompt:
    /usr/libexec/vimmite-ramalama run gemma "$@"

[private]
ramalama-run-laguna *prompt:
    /usr/libexec/vimmite-ramalama run laguna "$@"

[private]
ramalama-run-granite *prompt:
    /usr/libexec/vimmite-ramalama run granite "$@"

[private]
ramalama-run-nemotron *prompt:
    /usr/libexec/vimmite-ramalama run nemotron "$@"

[private]
ramalama-run-liquid *prompt:
    /usr/libexec/vimmite-ramalama run liquid "$@"

[private]
ramalama-run-north *prompt:
    /usr/libexec/vimmite-ramalama run north "$@"
