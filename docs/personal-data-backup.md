# Personal-data backup policy

Atomic deployments are the operating-system rollback mechanism. They do not
restore home directories, model weights, game saves, projects, or mutable
application state. Vimmite therefore standardizes on Restic for encrypted,
versioned personal-data backups. Restic is installed on the host, but no
repository, credentials, schedule, retention policy, or destination is created
by the image because those are user-specific secrets and storage decisions.

## Required copies

Use the 3-2-1 rule for data that cannot be recreated: keep the working copy,
one backup on separate storage, and one copy at another physical location.
The remote copy may be a Restic-supported cloud service, an SFTP host, or an
off-site disk. A permanently attached disk is not the only backup because it is
exposed to the same theft, electrical failure, and accidental deletion.

The default personal-data set is the user's home directory with cache and
re-downloadable bulk data excluded. It must include at least:

- documents, photos, `~/dev`, and `~/sync` content that is not already safely
  replicated elsewhere;
- shell, application, encryption-key, and other intentional configuration;
- `~/.var/app` state needed by important Flatpaks;
- non-cloud game saves and Steam `userdata`; and
- locally created or fine-tuned model data that cannot be downloaded again.

Do not back up replaceable Steam game installations, container images,
Distrobox roots, build outputs, general caches, or downloaded public model
weights in the normal personal-data job. Keep a manifest of downloadable model
IDs and checksums instead. If the cost of downloading model weights again is
unacceptable, put them in a separate Restic job and repository with a retention
and capacity policy sized for that data.

## Setup requirements

Choose the two backup destinations before relying on a Vimmite installation.
Initialize encrypted Restic repositories using Restic's documented repository
URL for each destination. Store the repository password in a password manager
or hardware-backed secret store, never in this repository or a world-readable
environment file.

Create and review an exclude file for re-downloadable data. At minimum consider
the following paths, adjusting them to the actual home layout:

```text
.cache
.local/share/containers
.local/share/Steam/steamapps/common
ai/models
```

Do not exclude all of `steamapps`: Proton prefixes can contain non-cloud saves.
Inspect each important game's save location and include it deliberately.

Run the personal-data job at least daily and the separate large-model job, if
used, after meaningful changes. Apply a documented retention policy and run
`restic check` regularly. A backup command returning success is not acceptance.

## Restore gate

Before V6 release, and at least quarterly afterward:

1. Record the machine, date, repository location, and snapshot ID without
   recording credentials.
2. Restore a project file, an application-state sample, and one important game
   save into a new temporary directory.
3. Compare the restored content with the source and open it with the relevant
   application where practical.
4. If irreplaceable model work is in scope, restore and validate a representative
   artifact from that repository too.
5. Record exclusions and confirm every excluded item is either disposable or
   protected by another tested system.

The corresponding physical checklist item remains open until this drill passes.
