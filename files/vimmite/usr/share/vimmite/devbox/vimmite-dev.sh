# Vimmite development-box defaults. Language versions remain project-owned.
export EDITOR="${EDITOR:-nvim}"
export VISUAL="${VISUAL:-nvim}"

# Distrobox shares HOME with the host. These paths allow project-managed mise,
# uv, Cargo, and user binaries to work in terminals and editor subprocesses
# without writing activation snippets into the host's shell files.
case ":${PATH}:" in *":${HOME}/.local/bin:"*) ;; *) PATH="${HOME}/.local/bin:${PATH}" ;; esac
case ":${PATH}:" in *":${HOME}/.local/share/mise/shims:"*) ;; *) PATH="${HOME}/.local/share/mise/shims:${PATH}" ;; esac
case ":${PATH}:" in *":${HOME}/.cargo/bin:"*) ;; *) PATH="${HOME}/.cargo/bin:${PATH}" ;; esac
export PATH
