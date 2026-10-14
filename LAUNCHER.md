# vimmite-v6 launcher

Run `./run.sh` for the menu, or select an explicit action from any directory:

```sh
/absolute/checkout/run.sh help
/absolute/checkout/run.sh info --json
/absolute/checkout/run.sh doctor --json
/absolute/checkout/run.sh doctor --action ACTION --json
/absolute/checkout/run.sh ACTION -- APP_ARGS
```

ISO builds require Podman, Skopeo, disk space and interactive sudo for rootful Lorax; local mode also needs BlueBuild. Existing build options/output/cache paths are retained and builds may overwrite their selected ISO. Source check prerequisites are listed in CONTRIBUTING.md. No build, registry access or privilege elevation occurs on default invocation.

| Action | Behavior |
| --- | --- |
| `iso-help` | Show ISO modes and options without building. |
| `check` | Run the existing source checks; optional argument selects one check. |
| `build` | Explicit ISO build; pass published/local and output/cache options. |

Default invocation only opens the menu. Setup/build actions must be selected explicitly.
Static doctor reports declared files/executables; it does not prove application health.
Missing prerequisites can be inspected per action without preparing unrelated actions.
Arguments are forwarded as separate values; use `ACTION -- ARGS` to avoid action-name ambiguity.
