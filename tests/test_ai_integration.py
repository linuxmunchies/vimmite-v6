"""Run with python3 -m unittest discover -s tests -v. No network or containers needed."""
import os
from pathlib import Path
import pty
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / 'files/vimmite/usr/libexec'


class AIIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)

    def subject_source(self, name, overrides=''):
        source = (LIB / name).read_text()
        # Load production functions without invoking the public entry point.
        if '\ncase "${1:-menu}" in' in source:
            source = source.split('\ncase "${1:-menu}" in')[0]
        elif '\naction="${1:-create}"' in source:
            source = source.split('\naction="${1:-create}"')[0]
        elif '\napp="${1:-}"' in source:
            source = source.split('\napp="${1:-}"')[0]
        else:
            source = source.rsplit('\nmain "$@"', 1)[0]
        source = re.sub(r'if \(\( EUID == 0 \)\); then.*?\nfi', '', source, flags=re.S)
        source = source.replace('source "${SCRIPT_DIR}/vimmite-strix-halo-common"',
                                f'source "{LIB}/vimmite-strix-halo-common"')
        # Menu terminal checks only: dispatch and labels stay production code.
        source = source.replace('[[ -t 0 ]] || { echo "The AI', 'true || { echo "The AI')
        source = source.replace('[[ ! -t 0 || ! -t 1 ]]', '[[ false == true ]]')
        # Route absolute helper calls through shell mocks, never host helpers.
        source = source.replace(' /usr/libexec/vimmite-', ' mock-vimmite-')
        overrides = overrides.replace('${1##*/}', '${1#mock-}')
        overrides = overrides.replace('CALLED:$1', 'CALLED:/usr/libexec/${1#mock-}')
        return source + '\n' + overrides + '\n'

    def run_functions(self, name, body, overrides=''):
        script = self.home / 'subject'
        script.write_text(self.subject_source(name, overrides) + body)
        return subprocess.run(['bash', str(script)], env={**os.environ, 'HOME': str(self.home)},
                              text=True, capture_output=True, timeout=10)

    def run_functions_tty(self, name, body, overrides=''):
        """Run the subject with a real pty on stdin/stdout, as a terminal user does."""
        script = self.home / 'subject-tty'
        script.write_text(self.subject_source(name, overrides) + body)
        controller, follower = pty.openpty()
        process = subprocess.Popen(['bash', str(script)], stdin=follower, stdout=follower,
                                   stderr=follower, close_fds=True,
                                   env={**os.environ, 'HOME': str(self.home)})
        os.close(follower)
        chunks = []
        try:
            while True:
                try:
                    chunk = os.read(controller, 65536)
                except OSError:
                    break
                if not chunk:
                    break
                chunks.append(chunk)
        finally:
            os.close(controller)
        process.wait(timeout=10)
        return b''.join(chunks).decode(errors='replace')

    def test_all_mega_menu_labels_dispatch(self):
        expected = ['install_menu', 'vimmite-ai-update menu', 'vimmite-ramalama',
                    'vimmite-strix-halo-ai', 'vimmite-strix-halo-comfyui', 'status_menu']
        for index, call in enumerate(expected, 2):
            with self.subTest(call=call):
                # choose receives prompt followed by the displayed labels.
                overrides = f'''
choose() {{ printf '%s\\n' "${{{index}}}"; }}
clear() {{ :; }}
pause_menu() {{ :; }}
install_menu() {{ echo install_menu; exit; }}
status_menu() {{ echo status_menu; exit; }}
command_not_found_handle() {{ echo "${{1##*/}} ${{*:2}}"; exit 0; }}
'''
                # External dispatch exits in its child, so bound menu to one iteration.
                overrides += 'choose() { if [[ -f "$HOME/chosen" ]]; then echo Back; else touch "$HOME/chosen"; printf "%s\\n" "${' + str(index) + '}"; fi; }\n'
                (self.home / 'chosen').unlink(missing_ok=True)
                result = self.run_functions('vimmite-ai', 'menu', overrides)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(call, result.stdout)

    def test_install_menu_cli_label_and_failure(self):
        result = self.run_functions('vimmite-ai', 'install_menu', '''
choose() { echo 'AI coding harnesses and CLIs'; }
command_not_found_handle() { echo "${1##*/} ${*:2}"; return 17; }
''')
        self.assertEqual(result.returncode, 17)
        self.assertIn('vimmite-install-ai-cli menu', result.stdout)

    def test_update_menu_every_label(self):
        actions = ['run_all', 'update_base_harnesses', 'update_devbox', 'update_comfyui',
                   'update_strix_halo', 'update_desktop_packages', 'update_ramalama']
        for index, action in enumerate(actions, 2):
            overrides = '\n'.join(f'{a}() {{ echo {a}; exit; }}' for a in actions)
            overrides += '\nchoose() { printf "%s\\n" "${' + str(index) + '}"; }'
            result = self.run_functions('vimmite-ai-update', 'menu', overrides)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(action, result.stdout)

    def test_run_all_aggregates_and_continues(self):
        result = self.run_functions('vimmite-ai-update', 'run_all', '''
bash() { echo "step:$2"; [[ "$2" != base ]]; }
''')
        self.assertEqual(result.returncode, 1)
        self.assertIn('step:ramalama', result.stdout)
        self.assertIn('base update failed', result.stderr)

    def test_harness_failure_propagates(self):
        result = self.run_functions('vimmite-ai-update', 'update_base_harnesses', '''
host_has_command() { [[ "$1" == codex ]]; }
box_has_command() { return 1; }
command_not_found_handle() { return 19; }
''')
        self.assertEqual(result.returncode, 1)

    def test_devbox_update_preserves_packages(self):
        result = self.run_functions('vimmite-devbox', 'update_box', '''
check_host() { :; }
box_exists() { :; }
in_box() { printf '%s\\n' "$*"; }
build_image() { exit 97; }
distrobox() { exit 98; }
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('sudo dnf upgrade', result.stdout)

    def test_failed_strix_pull_never_removes_container(self):
        result = self.run_functions('vimmite-strix-halo-ai', 'update_backend vulkan', '''
require_commands() { :; }
require_strix_halo() { :; }
require_device_access() { :; }
have_container() { :; }
podman() { echo "$*"; return 23; }
distrobox() { echo DELETED; }
''')
        self.assertEqual(result.returncode, 23, result.stderr)
        self.assertNotIn('DELETED', result.stdout)

    def test_failed_chatgpt_download_never_installs_stale_rpm(self):
        cache = self.home / '.cache/vimmite-ai'
        cache.mkdir(parents=True)
        (cache / 'chatgpt.x86_64.rpm').write_text('old')
        result = self.run_functions('vimmite-install-ai-app', 'install_chatgpt_host', '''
require_commands() { :; }
uname() { echo x86_64; }
curl() { return 22; }
sudo() { echo INSTALLED; }
''')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('INSTALLED', result.stdout)
        self.assertEqual((cache / 'chatgpt.x86_64.rpm').read_text(), 'old')

    def test_chatgpt_atomic_update_replaces_existing_local_rpm_request(self):
        result = self.run_functions('vimmite-install-ai-app', 'install_chatgpt_host', '''
require_commands() { :; }
download_chatgpt() { printf '%s\\n' "$HOME/chatgpt-current.rpm"; }
command() { [[ "$1" == -v && "$2" == rpm-ostree ]]; }
rpm() { [[ "$1" == -q && "$2" == chatgpt ]]; }
sudo() { printf 'SUDO:%s\\n' "$*"; }
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('SUDO:rpm-ostree install --uninstall=chatgpt', result.stdout)
        self.assertIn('chatgpt-current.rpm', result.stdout)
        self.assertNotIn('--idempotent', result.stdout)

    def test_chatgpt_atomic_first_install_still_layers_idempotently(self):
        result = self.run_functions('vimmite-install-ai-app', 'install_chatgpt_host', '''
require_commands() { :; }
download_chatgpt() { printf '%s\\n' "$HOME/chatgpt-current.rpm"; }
command() { [[ "$1" == -v && "$2" == rpm-ostree ]]; }
rpm() { return 1; }
rpm-ostree() { [[ "$1" == status ]] && printf '{}\\n'; }
sudo() { printf 'SUDO:%s\\n' "$*"; }
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('SUDO:rpm-ostree install --idempotent', result.stdout)
        self.assertNotIn('--uninstall=chatgpt', result.stdout)

    def test_desktop_update_refreshes_host_chatgpt_via_local_rpm_installer(self):
        result = self.run_functions('vimmite-ai-update', 'update_desktop_packages', '''
rpm() { [[ "$1" == -q && "$2" == chatgpt ]]; }
devbox_exists() { return 1; }
command_not_found_handle() { printf 'CALLED:%s %s\\n' "$1" "$*"; }
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('CALLED:/usr/libexec/vimmite-install-ai-app', result.stdout)
        self.assertIn('chatgpt host', result.stdout)
        self.assertNotIn('rpm-ostree upgrade', result.stdout)

    def test_desktop_update_refreshes_container_chatgpt_via_local_rpm_installer(self):
        result = self.run_functions('vimmite-ai-update', 'update_desktop_packages', '''
rpm() { return 1; }
devbox_exists() { return 0; }
distrobox() {
    case "$*" in
        *'rpm -q chatgpt'*) return 0 ;;
        *'rpm -q claude-desktop-unofficial'*) return 1 ;;
        *) printf 'DISTROBOX:%s\\n' "$*" ;;
    esac
}
command_not_found_handle() { printf 'CALLED:%s %s\\n' "$1" "$*"; }
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('CALLED:/usr/libexec/vimmite-install-ai-app', result.stdout)
        self.assertIn('chatgpt container', result.stdout)

    def test_container_cli_environment_is_separate(self):
        result = self.run_functions('vimmite-install-ai-cli', 'install_cli codex container', '''
ensure_devbox() { :; }
distrobox() { printf '%s\\n' "$@"; }
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f'HOME={self.home}/.local/share/vimmite-ai/container', result.stdout)
        self.assertTrue((self.home / '.local/share/vimmite-ai/container/installed/codex').is_file())
        self.assertTrue((self.home / '.local/bin/codex-container').is_file())
        self.assertFalse((self.home / '.local/bin/codex').exists())

    def test_container_exec_attaches_a_terminal_when_one_exists(self):
        # Every harness and every upstream installer is a terminal program;
        # forcing --no-tty left /dev/tty unopenable inside the box.
        overrides = """
ensure_devbox() { :; }
distrobox() { printf '%s\\n' "$@"; }
"""
        with_tty = self.run_functions_tty('vimmite-install-ai-cli',
                                          'install_cli codex container', overrides)
        self.assertIn('vimmite-dev', with_tty)
        self.assertNotIn('--no-tty', with_tty)

    def test_container_exec_falls_back_to_no_tty_without_a_terminal(self):
        result = self.run_functions('vimmite-install-ai-cli', 'install_cli codex container', """
ensure_devbox() { :; }
distrobox() { printf '%s\\n' "$@"; }
""")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--no-tty', result.stdout)

    def test_container_installer_is_executed_by_path_not_piped_on_stdin(self):
        # Feeding the installer in on stdin consumed the terminal, so prompts
        # and progress bars had nowhere to go.
        result = self.run_functions('vimmite-install-ai-cli', 'install_cli grok container', """
ensure_devbox() { :; }
download() { printf '#!/bin/sh\\n' > "$2"; }
distrobox() { printf '%s\\n' "$@"; }
""")
        self.assertEqual(result.returncode, 0, result.stderr)
        staged = f'{self.home}/.local/share/vimmite-ai/container/.cache/vimmite-ai/installers/installer.'
        argv = result.stdout.splitlines()
        self.assertTrue(any(line.startswith(staged) for line in argv), result.stdout)
        self.assertNotIn('-s', argv)

    def test_dsh_tracks_the_bleeding_edge_dist_tag(self):
        result = self.run_functions('vimmite-install-ai-cli', 'install_cli dsh container', """
ensure_devbox() { :; }
distrobox() { printf '%s\\n' "$@"; }
""")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('@deepseek-ai/dsh@alpha', result.stdout)
        self.assertIn('@openai/codex@latest',
                      self.run_functions('vimmite-install-ai-cli', 'install_cli codex container', """
ensure_devbox() { :; }
distrobox() { printf '%s\\n' "$@"; }
""").stdout)

    def test_npm_dist_tag_is_overridable(self):
        os.environ['VIMMITE_AI_TAG_DSH'] = '0.1.6-alpha.2'
        self.addCleanup(os.environ.pop, 'VIMMITE_AI_TAG_DSH', None)
        result = self.run_functions('vimmite-install-ai-cli', 'install_cli dsh container', """
ensure_devbox() { :; }
distrobox() { printf '%s\\n' "$@"; }
""")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('@deepseek-ai/dsh@0.1.6-alpha.2', result.stdout)

    def test_installer_arguments_reach_the_upstream_script(self):
        result = self.run_functions('vimmite-install-ai-cli',
                                    'install_cli hermes container --skip-browser', """
ensure_devbox() { :; }
download() { printf '#!/bin/sh\\n' > "$2"; }
distrobox() { printf '%s\\n' "$@"; }
""")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--skip-browser', result.stdout.splitlines())

    def test_cli_menu_failure_not_swallowed(self):
        result = self.run_functions('vimmite-install-ai-cli', 'menu', '''
choose_cli() { echo 'Install or update Codex'; }
install_cli_with_target() { return 31; }
''')
        self.assertEqual(result.returncode, 31)

    def test_comfyui_both_targets_update_independently(self):
        result = self.run_functions('vimmite-install-ai-app', '''
install_comfyui host
install_comfyui container
update_comfyui
''', '''
comfy_install_host() { echo "HOST:$COMFY_SOURCE:$COMFY_VENV"; }
comfy_install_container() { echo "BOX:$COMFY_SOURCE:$COMFY_VENV"; }
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count('/host/ComfyUI:'), 2)
        self.assertEqual(result.stdout.count('/container/ComfyUI:'), 2)

    def test_ramalama_only_updates_existing_managed_install(self):
        overrides = 'command_not_found_handle() { echo "CALLED:$1"; }'
        result = self.run_functions('vimmite-ai-update', 'update_ramalama', overrides)
        self.assertNotIn('CALLED:', result.stdout)
        binary = self.home / '.local/share/ramalama-cli/bin/ramalama'
        binary.parent.mkdir(parents=True)
        binary.touch(mode=0o755)
        result = self.run_functions('vimmite-ai-update', 'update_ramalama', overrides)
        self.assertIn('CALLED:/usr/libexec/vimmite-ramalama-install', result.stdout)

    def test_successful_strix_pull_precedes_removal(self):
        result = self.run_functions('vimmite-strix-halo-ai', 'update_backend vulkan', '''
require_commands() { :; }
require_strix_halo() { :; }
require_device_access() { :; }
have_container() { :; }
podman() { echo "podman:$*"; }
distrobox() { echo "distrobox:$*"; }
cleanup_old_repository_images() { :; }
install_wrappers() { :; }
verify_backend() { :; }
container_exec() { :; }
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertLess(result.stdout.index('podman:pull'), result.stdout.index('distrobox:rm'))

    def test_container_cli_failure_does_not_record_install(self):
        result = self.run_functions('vimmite-install-ai-cli', 'install_cli codex container', '''
ensure_devbox() { :; }
distrobox() { return 42; }
''')
        self.assertEqual(result.returncode, 42)
        self.assertNotIn('is available', result.stdout)
        self.assertFalse((self.home / '.local/share/vimmite-ai/container/installed/codex').exists())

    def test_container_comfy_script_uses_own_checkout_and_venv(self):
        result = self.run_functions('vimmite-install-ai-app', 'comfy_install_container', '''
ensure_devbox() { :; }
box_shell() { cat; }
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('comfy_root="${HOME}/.local/share/vimmite-comfyui/container"', result.stdout)
        self.assertIn('comfy_source="${comfy_root}/ComfyUI"', result.stdout)
        self.assertIn('comfy_venv="${comfy_root}/venv"', result.stdout)
        self.assertIn('pip install -U --pre comfyui-manager', result.stdout)

    def test_generic_comfy_installs_and_enables_manager(self):
        source = (LIB / 'vimmite-install-ai-app').read_text()
        self.assertEqual(source.count('pip install -U --pre comfyui-manager'), 2)
        self.assertIn('--enable-manager', source)
        host = self.run_functions('vimmite-install-ai-app', 'type comfy_install_host')
        self.assertEqual(host.returncode, 0, host.stderr)
        self.assertIn('pip install -U --pre comfyui-manager', host.stdout)

    def test_comfy_model_catalog_lists_manifest_choices_with_sizes(self):
        result = self.run_functions('vimmite-strix-halo-comfyui', 'model_catalog')
        self.assertEqual(result.returncode, 0, result.stderr)
        entries = [line for line in result.stdout.splitlines() if line]
        self.assertEqual(len(entries), 35)
        for model_id in (
            'qwen-image-21', 'qwen-image', 'qwen-gguf', 'krea-turbo', 'ideogram',
            'glm-image', 'qwen-edit', 'sam', 'realesrgan', 'minimax', 'ltx-dev',
            'hunyuan-i2v', 'wan-i2v', 'wan-i2v-lightning',
        ):
            self.assertTrue(any(line.startswith(model_id + '|') for line in entries), model_id)
        self.assertTrue(all(line.split('|')[1] in {
            'image', 'edit', 'segment', 'upscale', 'video',
        } for line in entries))
        self.assertTrue(all('(' in line and ')' in line for line in entries))

    def test_comfy_model_manifest_preserves_dependencies_and_diffusers_layout(self):
        result = self.run_functions('vimmite-strix-halo-comfyui', '''
model_manifest qwen-image-21
model_manifest krea-turbo
model_manifest qwen-gguf
model_manifest glm-image
model_manifest wan-t2v-lightning
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Comfy-Org/Qwen-Image-2.1|diffusion_models/qwen_image_2.1_bf16.safetensors|diffusion_models/qwen_image_2.1_bf16.safetensors', result.stdout)
        self.assertIn('Comfy-Org/Krea-2|diffusion_models/krea2_turbo_bf16.safetensors|diffusion_models/krea2_turbo_bf16.safetensors', result.stdout)
        self.assertIn('unsloth/Qwen2.5-VL-7B-Instruct-GGUF|Qwen2.5-VL-7B-Instruct-UD-Q4_K_XL.gguf|text_encoders/Qwen2.5-VL-7B-Instruct-UD-Q4_K_XL.gguf', result.stdout)
        self.assertIn('zai-org/GLM-Image|*|diffusers/GLM-Image', result.stdout)
        self.assertIn('lightx2v/Wan2.2-Lightning|Wan2.2-T2V-A14B-4steps-lora-rank64-Seko-V2.0/high_noise_model.safetensors|loras/Wan2.2-T2V-A14B-4steps-lora-rank64-Seko-V2.0/high_noise_model.safetensors', result.stdout)

    def test_comfy_model_download_uses_new_root_and_xet_hf(self):
        result = self.run_functions('vimmite-strix-halo-comfyui', '''
download_model demo
test -f "$MODEL_DIR/diffusion_models/example.safetensors"
test ! -e "$MODEL_DIR/split_files/diffusion_models/example.safetensors"
''', '''
model_manifest() { printf '%s\\n' 'example/repo|split_files/diffusion_models/example.safetensors|diffusion_models/example.safetensors'; }
hf() { :; }
hf_download() {
    [[ "$1" == download && "$2" == example/repo && "$3" == split_files/diffusion_models/example.safetensors ]]
    [[ "$4" == --local-dir ]]
    mkdir -p "$5/split_files/diffusion_models"
    printf 'test payload\\n' > "$5/$3"
    echo "$5/$3"
}
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f'Download complete: demo', result.stdout)
        self.assertIn(f'{self.home}/ai/comfy-models', result.stdout)

    def test_comfy_model_download_failure_propagates(self):
        result = self.run_functions('vimmite-strix-halo-comfyui', 'download_model demo', '''
model_manifest() { printf '%s\\n' 'example/repo|example.safetensors|checkpoints/example.safetensors'; }
hf() { :; }
hf_download() { return 23; }
''')
        self.assertEqual(result.returncode, 23)

    def test_comfy_nas_download_copies_into_catalog_destination(self):
        result = self.run_functions('vimmite-strix-halo-comfyui', '''
model_manifest() { printf '%s\\n' 'nas/repo|example.safetensors|diffusion_models/example.safetensors'; }
rclone() { :; }
rclone_smb() {
    case "$1" in
        lsd) return 0 ;;
        lsjson) printf '%s\\n' '{"IsDir":false,"Size":11}' ;;
        copyto)
            mkdir -p -- "$(dirname -- "$3")"
            printf 'nas payload' > "$3"
            ;;
        *) return 0 ;;
    esac
}
download_model_nas demo
test -f "$MODEL_DIR/diffusion_models/example.safetensors"
test "$(cat "$MODEL_DIR/diffusion_models/example.safetensors")" = 'nas payload'
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('NAS download complete: demo', result.stdout)
        self.assertIn(f'{self.home}/ai/comfy-models/diffusion_models/example.safetensors', result.stdout)

    def test_comfy_nas_download_preserves_diffusers_directory(self):
        result = self.run_functions('vimmite-strix-halo-comfyui', '''
model_manifest() { printf '%s\\n' 'zai-org/GLM-Image|*|diffusers/GLM-Image'; }
rclone() { :; }
rclone_smb() {
    case "$1" in
        lsd) return 0 ;;
        lsjson)
            if [[ "$2" == */model_index.json ]]; then
                printf '%s\\n' '{"IsDir":false,"Size":2}'
            else
                printf '%s\\n' '{"IsDir":true,"Size":-1}'
            fi
            ;;
        copy)
            mkdir -p -- "$3"
            printf '{}\\n' > "$3/model_index.json"
            ;;
        check) return 0 ;;
        *) return 0 ;;
    esac
}
download_model_nas glm-image
test -s "$MODEL_DIR/diffusers/GLM-Image/model_index.json"
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('NAS download complete: glm-image', result.stdout)

    def test_comfy_model_status_reports_missing_partial_complete(self):
        result = self.run_functions('vimmite-strix-halo-comfyui', '''
model_manifest() { printf '%s\\n' 'example/repo|a.safetensors|diffusion_models/a.safetensors' 'example/repo|b.safetensors|vae/b.safetensors'; }
model_status demo
mkdir -p "$MODEL_DIR/diffusion_models" "$MODEL_DIR/vae"
printf 'a' > "$MODEL_DIR/diffusion_models/a.safetensors"
model_status demo
printf 'b' > "$MODEL_DIR/vae/b.safetensors"
model_status demo
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ['missing 0 2', 'partial 1 2', 'complete 2 2'])

    def test_comfy_nas_upload_copies_catalog_destination(self):
        result = self.run_functions('vimmite-strix-halo-comfyui', '''
model_manifest() { printf '%s\\n' 'nas/repo|example.safetensors|diffusion_models/example.safetensors'; }
mkdir -p "$MODEL_DIR/diffusion_models"
printf 'local payload' > "$MODEL_DIR/diffusion_models/example.safetensors"
rclone() { :; }
rclone_smb() {
    case "$1" in
        lsd) return 0 ;;
        lsjson) printf '%s\\n' '{"IsDir":false,"Size":13}' ;;
        copyto)
            printf '%s\\n' "uploaded:$2->$3"
            ;;
        *) return 0 ;;
    esac
}
upload_model demo
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('NAS upload complete: demo', result.stdout)
        self.assertIn(f'{self.home}/ai/comfy-models/diffusion_models/example.safetensors', result.stdout)
        self.assertIn('foxraid.local', result.stdout)

    def test_comfy_nas_upload_skips_missing_local_files(self):
        result = self.run_functions('vimmite-strix-halo-comfyui', '''
model_manifest() { printf '%s\\n' 'nas/repo|example.safetensors|diffusion_models/example.safetensors'; }
rclone() { :; }
rclone_smb() { return 0; }
upload_model demo
''')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Nothing local to upload for demo', result.stderr)

    def test_comfy_download_menu_exposes_nas_source_and_overrides(self):
        source = (LIB / 'vimmite-strix-halo-comfyui').read_text()
        self.assertIn('"Download from Hugging Face"', source)
        self.assertIn('"Download from NAS"', source)
        self.assertIn('"Upload to NAS"', source)
        self.assertIn('"Full status list"', source)
        self.assertIn('"Downloads (${running} running)"', source)
        self.assertIn('"Scan NAS"', source)
        self.assertIn('queue_job', source)
        self.assertIn('upload-model MODEL_ID', source)
        self.assertIn('COMFYUI_NAS_HOST', source)
        self.assertIn('foxraid.local', source)
        self.assertIn('//${COMFYUI_NAS_HOST}/${COMFYUI_NAS_SHARE}/${COMFYUI_NAS_SUBDIR}', source)
        self.assertIn("disk=%-5s NAS=%-5s", source)
        self.assertIn('status_cell', source)
        self.assertIn('Never put', source)
        self.assertIn('qwen-image-21|image|', source)
        self.assertIn('krea-turbo|image|', source)
        self.assertLess(source.index('qwen-image-21|image|'), source.index('krea-turbo|image|'))
        self.assertLess(source.index('krea-turbo|image|'), source.index('qwen-image|image|'))
        self.assertIn('readonly MODEL_DIR="${HOME}/ai/comfy-models"', source)
        self.assertIn('readonly OUTPUT_DIR="${HOME}/ai/comfy-outputs"', source)
        self.assertIn('readonly INPUT_DIR="${HOME}/ai/comfy-inputs"', source)
        self.assertIn('readonly USER_ROOT="${HOME}/ai/comfy-user"', source)
        self.assertNotIn('readonly OUTPUT_DIR="${HOME}/comfy-outputs"', source)
        self.assertNotIn('readonly MODEL_DIR="${HOME}/comfy-models"', source)

    def test_comfy_parse_model_choice_reads_plain_status_prefixes(self):
        result = self.run_functions('vimmite-strix-halo-comfyui', '''
parse_model_choice "disk=yes   NAS=yes   qwen-image-21: Qwen Image 2.1 7B BF16"
parse_model_choice "disk=2/3   NAS=no    krea-turbo: Krea 2 Turbo BF16"
parse_model_choice "disk=no    NAS=?     anima: Anima Aesthetic v1.1"
parse_job_choice "running  hf:qwen-image-21"
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), [
            'qwen-image-21', 'krea-turbo', 'anima', 'hf qwen-image-21',
        ])

    def test_comfy_queue_job_runs_download_in_background(self):
        result = self.run_functions('vimmite-strix-halo-comfyui', '''
catalog_entry() { printf '%s\\n' 'demo|image|Demo model'; }
download_model() { printf 'bg-download %s\\n' "$1"; }
queue_job demo hf
for _ in 1 2 3 4 5 6 7 8 9 10; do
    [[ -s "$JOB_ROOT/hf.demo.log" ]] && break
    sleep 0.05
done
grep -q 'bg-download demo' "$JOB_ROOT/hf.demo.log"
test -f "$JOB_ROOT/hf.demo.pid"
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Queued hf demo', result.stdout)
        self.assertIn('jobs keep running', result.stdout)

    def test_comfy_second_hf_job_waits_while_one_runs(self):
        result = self.run_functions('vimmite-strix-halo-comfyui', '''
catalog_entry() { printf '%s|image|%s\\n' "$1" "$1"; }
download_model() { printf 'start-%s\\n' "$1"; sleep 3; printf 'done-%s\\n' "$1"; }
queue_job one hf
queue_job two hf
test -f "$JOB_ROOT/hf.one.pid"
test -f "$JOB_ROOT/hf.two.queued"
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Queued hf one', result.stdout)
        self.assertIn('Queued hf two', result.stdout)

    def test_comfy_status_table_lists_qwen21_and_krea(self):
        result = self.run_functions('vimmite-strix-halo-comfyui', 'print_model_status image')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('disk=this PC', result.stdout)
        self.assertIn('qwen-image-21', result.stdout)
        self.assertIn('krea-turbo', result.stdout)
        self.assertLess(result.stdout.index('qwen-image-21'), result.stdout.index('krea-turbo'))

    def test_comfy_job_progress_reads_percent_from_log(self):
        result = self.run_functions('vimmite-strix-halo-comfyui', '''
mkdir -p "$JOB_ROOT"
printf '%s\\n' 'Downloading repo/qwen3vl_8b_bf16.safetensors -> dest' > "$JOB_ROOT/hf.demo.log"
printf '\\rreconstructing file: 42%% | 1.07GB / 17.5GB' >> "$JOB_ROOT/hf.demo.log"
job_progress hf demo
echo
printf '%s\\n' \
  'PROGRESS start 1/2 foo.safetensors 1000' \
  'Uploading foo -> remote' \
  '2026/09/20 19:38:50 INFO  :   120.027 MiB / 810.250 MiB, 15%, 30.019 MiB/s, ETA 22s' \
  > "$JOB_ROOT/upload.demo.log"
job_progress upload demo 2
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        self.assertRegex(lines[0], r'42%')
        self.assertRegex(lines[1], r'\d+%')
        self.assertIn('120.027MiB/810.250MiB', lines[1])

    def test_comfy_job_progress_reads_byte_watcher(self):
        result = self.run_functions('vimmite-strix-halo-comfyui', '''
mkdir -p "$JOB_ROOT"
printf '%s\\n' \
  'PROGRESS expect 10000000000' \
  'PROGRESS start 1/1 foo.safetensors 10000000000' \
  'PROGRESS bytes 2500000000' \
  > "$JOB_ROOT/hf.bytes.log"
job_progress hf bytes 1
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertRegex(result.stdout, r'25%')

    def test_comfy_nas_status_uses_scanned_index(self):
        result = self.run_functions('vimmite-strix-halo-comfyui', '''
model_manifest() { printf '%s\\n' 'r|a.safetensors|diffusion_models/a.safetensors' 'r|b.safetensors|vae/b.safetensors'; }
mkdir -p "$(dirname "$NAS_INDEX")"
printf '%s\\n' 'diffusion_models/a.safetensors' > "$NAS_INDEX"
date +%s > "$NAS_STAMP"
nas_model_status demo
status_cell partial 1 2
status_cell complete 2 2
status_cell unknown 0 0
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('partial 1 2', result.stdout)
        self.assertIn('1/2', result.stdout)
        self.assertIn('yes', result.stdout)
        self.assertIn('?', result.stdout)

    def test_comfy_migrates_legacy_inputs_when_dest_missing(self):
        result = self.run_functions('vimmite-strix-halo-comfyui', '''
mkdir -p "$HOME/comfy-inputs"
printf 'legacy-input\\n' > "$HOME/comfy-inputs/sentinel.txt"
ensure_host_data stable
test -f "$HOME/ai/comfy-inputs/sentinel.txt"
test -L "$HOME/comfy-inputs"
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.home / 'ai/comfy-inputs/sentinel.txt').read_text(), 'legacy-input\n')
        self.assertTrue((self.home / 'comfy-inputs').is_symlink())
        self.assertIn('Migrating leftover', result.stdout)

    def test_comfy_migrates_leftover_models_into_model_dir(self):
        result = self.run_functions('vimmite-strix-halo-comfyui', '''
mkdir -p "$HOME/comfy-models/diffusion_models" "$HOME/ai/comfy-models/vae"
printf 'old-model\\n' > "$HOME/comfy-models/diffusion_models/sentinel.safetensors"
printf 'kept\\n' > "$HOME/ai/comfy-models/vae/existing.safetensors"
ensure_host_data stable
test -f "$MODEL_DIR/diffusion_models/sentinel.safetensors"
test "$(cat "$MODEL_DIR/diffusion_models/sentinel.safetensors")" = 'old-model'
test -f "$MODEL_DIR/vae/existing.safetensors"
test -f "$HOME/comfy-models/diffusion_models/sentinel.safetensors"
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            (self.home / 'ai/comfy-models/diffusion_models/sentinel.safetensors').read_text(),
            'old-model\n',
        )
        self.assertEqual((self.home / 'ai/comfy-models/vae/existing.safetensors').read_text(), 'kept\n')
        self.assertTrue((self.home / 'comfy-models/diffusion_models/sentinel.safetensors').is_file())
        self.assertIn('Merging leftover', result.stdout)

    def test_strix_comfy_installs_and_enables_manager(self):
        source = (LIB / 'vimmite-strix-halo-comfyui').read_text()
        self.assertIn('pip install -U --pre comfyui-manager', source)
        self.assertIn('--enable-manager', source)
        result = self.run_functions('vimmite-strix-halo-comfyui', '''
container_exec() { printf '%s\\n' "$*"; }
log() { printf '%s\\n' "$*"; }
ensure_comfyui_manager demo-container 1
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('/opt/venv/bin/python -m pip install -U --pre comfyui-manager', result.stdout)
        self.assertIn('Installing ComfyUI-Manager in demo-container', result.stdout)

    def test_strix_menu_separates_llm_and_comfy_downloads(self):
        source = (LIB / 'vimmite-strix-halo-ai').read_text()
        self.assertIn("'4. Download recommended LLM models'", source)
        self.assertIn("'5. Manage ComfyUI models'", source)
        self.assertIn('"${COMFYUI_MANAGER}" download-models', source)

    def test_recipe_forwards_target(self):
        recipe = (ROOT / 'files/justfiles/vimmite.just').read_text()
        self.assertIn('install-ai-cli tool="menu" target="host":\n    /usr/libexec/vimmite-install-ai-cli "$@"', recipe)


if __name__ == '__main__':
    unittest.main()
