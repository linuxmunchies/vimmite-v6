# Working on Vimmite

## Local checks

Run the same checks as CI from the repository root:

```bash
python3 scripts/check.py
```

Dependencies: Bash, Python 3 with PyYAML, ShellCheck (0.9 or newer), Just 1.58.0,
and BlueBuild 0.9.37. The workflow installs its tools on a fresh Ubuntu runner;
it does not install packages on your desktop. BlueBuild validation needs network
access to its schemas. See the [BlueBuild CLI installation guide](https://blue-build.org/how-to/local/).

Individual checks are available as `python3 scripts/check.py bash`,
`shellcheck`, `just`, or `recipes`.

The checks cover:

1. Bash syntax in build scripts and installed helpers, including extensionless files.
2. ShellCheck warnings and errors. Informational/style suggestions do not block CI.
3. Just parsing, Bash syntax and ShellCheck for embedded recipe bodies, and
   existence/executable permissions of referenced Vimmite helpers.
4. BlueBuild schema validation and existence of local module, script, and overlay inputs.

These checks never execute setup recipes, install applications, or change host
settings. They do not prove that image-provided commands work on hardware.
The existing image build runs after validation passes. Pushes and schedules
publish automatically; pull requests build without pushing or signing.

## Code conventions

- Group image dependencies by purpose in `recipes/modules/`.
- Keep `ujust` names, defaults, help, and short commands in `files/justfiles/`.
  Put longer shell workflows in executable `files/vimmite/usr/libexec/vimmite-*`
  helpers. Preserve the public command names when refactoring.
- Use Bash, four-space indentation for new runtime helpers, quoted expansions,
  arrays for command arguments, and `set -euo pipefail` where errors should stop
  execution. Diagnostics that intentionally continue should handle failures explicitly.
- Pass user arguments with `"$@"` or positional parameters rather than inserting
  them into shell source. Keep setup changes opt-in where appropriate, preserve
  user configuration, and document the undo path.
- Pin and checksum external artifacts downloaded during image composition.
- Keep build output and credentials out of Git. Only the public Cosign key is tracked.
- Update the relevant guide when behavior changes. Current instructions belong
  in `docs/`; historical audits and migration records belong in `docs/history/`.

After changes that affect the image, build locally with
`bluebuild build --no-sign recipes/vimmite.yml` when practical. Record hardware
results against an image digest using [the checklist](docs/test-checklist.md).
Physical tests establish hardware confidence separately from automatic publication.
