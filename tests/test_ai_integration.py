"""Run with python3 -m unittest discover -s tests -v. No network or containers needed."""
import os
from pathlib import Path
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

    def run_functions(self, name, body, overrides=''):
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
        script = self.home / 'subject'
        script.write_text(source + '\n' + overrides + '\n' + body)
        return subprocess.run(['bash', str(script)], env={**os.environ, 'HOME': str(self.home)},
                              text=True, capture_output=True, timeout=10)

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

    def test_comfy_model_catalog_lists_manifest_choices_with_sizes(self):
        result = self.run_functions('vimmite-strix-halo-comfyui', 'model_catalog')
        self.assertEqual(result.returncode, 0, result.stderr)
        entries = [line for line in result.stdout.splitlines() if line]
        self.assertEqual(len(entries), 33)
        for model_id in (
            'qwen-image', 'qwen-gguf', 'ideogram', 'glm-image', 'qwen-edit',
            'sam', 'realesrgan', 'minimax', 'ltx-dev', 'hunyuan-i2v',
            'wan-i2v', 'wan-i2v-lightning',
        ):
            self.assertTrue(any(line.startswith(model_id + '|') for line in entries), model_id)
        self.assertTrue(all('(' in line and ')' in line for line in entries))

    def test_comfy_model_manifest_preserves_dependencies_and_diffusers_layout(self):
        result = self.run_functions('vimmite-strix-halo-comfyui', '''
model_manifest qwen-gguf
model_manifest glm-image
model_manifest wan-t2v-lightning
''')
        self.assertEqual(result.returncode, 0, result.stderr)
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

    def test_comfy_download_menu_exposes_nas_source_and_overrides(self):
        source = (LIB / 'vimmite-strix-halo-comfyui').read_text()
        self.assertIn("source=\"$(choose 'Download source' 'Hugging Face' NAS Back)\"", source)
        self.assertIn('download-model-nas MODEL_ID', source)
        self.assertIn('COMFYUI_NAS_HOST', source)
        self.assertIn('//${COMFYUI_NAS_HOST}/${COMFYUI_NAS_SHARE}/${COMFYUI_NAS_SUBDIR}', source)

    def test_strix_menu_separates_llm_and_comfy_downloads(self):
        source = (LIB / 'vimmite-strix-halo-ai').read_text()
        self.assertIn("'4. Download recommended LLM models'", source)
        self.assertIn("'5. Download ComfyUI models'", source)
        self.assertIn('"${COMFYUI_MANAGER}" download-models', source)

    def test_recipe_forwards_target(self):
        recipe = (ROOT / 'files/justfiles/vimmite.just').read_text()
        self.assertIn('install-ai-cli tool="menu" target="host":\n    /usr/libexec/vimmite-install-ai-cli "$@"', recipe)


if __name__ == '__main__':
    unittest.main()
