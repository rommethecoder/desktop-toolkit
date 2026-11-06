# Desktop Toolkit

Selected KDE desktop settings backups, a managed Rofi launcher toggle, and an explicit audio-output switch. Built from recurring tasks on a CachyOS/Plasma desktop; configuration is independent of the author's machine.

The backup utility checks the destination filesystem UUID, writes a private archive, verifies a SHA-256 manifest, and restores only into a new staging directory. It complements filesystem snapshots when desktop configuration lives on a separate home subvolume. It is not a full-system backup or an encrypted/offsite backup service.

## Requirements

Linux, Python 3.11+, and `findmnt` (util-linux). The audio utility needs `pactl` (PulseAudio or PipeWire-Pulse). The launcher needs Rofi and a private `XDG_RUNTIME_DIR`. No Python runtime dependencies.

Run from this checkout, or install with `pipx install .`:

```sh
python -m desktop_toolkit.backup --help
python -m unittest discover -s tests -v
```

## Back up selected settings

1. Copy `examples/backup.json` outside the repository and edit its destination, filesystem UUID and allowlist. Use `findmnt -no UUID -T /path/to/mounted/backup-drive` to inspect the UUID. Create the intended destination directory on that drive first.
2. Review every selected path. Settings may contain private paths or identifiers; these archives are not suitable for public upload. Browser profiles, SSH credentials and whole `.config` directories are deliberately absent from the example.
3. Preview and create:

```sh
python -m desktop_toolkit.backup backup --config /path/to/backup.json --dry-run
python -m desktop_toolkit.backup backup --config /path/to/backup.json
python -m desktop_toolkit.backup verify /path/to/desktop-settings-TIMESTAMP.tar.gz
```

If the drive is absent or the filesystem UUID differs, creation stops before writing an archive. The utility never creates mount points, edits fstab, runs sudo or changes the existing desktop. Optional missing paths are reported; a selection containing no files is rejected. Symlinks and special files are rejected. Maximum selected content is 512 MiB.

## Restore into a staging directory

```sh
python -m desktop_toolkit.backup restore /path/to/archive.tar.gz --target /path/to/new-staging-directory
```

The target must not already exist. Inspect the restored files and compare them with your current settings before manually merging selected changes. Restored files are private (0600); executable scripts, if explicitly included, need reviewed permissions before use. No live-home overwrite is implemented. Archive checksums detect corruption; they do not authenticate an archive supplied by someone else. Concurrent filesystem changes are not captured as an atomic snapshot.

## Small utilities

List your audio outputs with `pactl list short sinks`, then pass two actual sink names:

```sh
python -m desktop_toolkit.audio 'FIRST_SINK_NAME' 'SECOND_SINK_NAME'
```

This changes the default output only. Existing streams may remain attached to their current sink; per-application routing is outside this utility's scope.

Bind `python -m desktop_toolkit.rofi` to a desktop shortcut, using this checkout as the working directory or installing the entry point `rofi-toggle`. It supervises its own `rofi -show drun` process and uses a runtime lock rather than a broad process-name kill. It does not manage Rofi instances launched another way. Rofi's graphical appearance remains controlled by your existing configuration.

## Verification and provenance

Automated tests use temporary directories and mocked mount/audio/launcher interfaces. Tests cover archive round-trip, mount mismatch, staged-restore overwrite rejection, symlinks, traversal, tampering, dry-run behavior and launcher isolation. A fixture restore is tested; restoring a real user's complete desktop and interactive Rofi/audio behavior on multiple distributions remain manual checks.

Original implementation by Terry (Romme) Felton, adapted from his personal CachyOS workflow with AI assistance. MIT licensed. Proposed changes should include a reproduction/test and avoid bundling personal dotfiles, binaries or credentials.

## How this started

[Read the project history](docs/PROJECT_HISTORY.md) for the original problem, the choices behind the first release and the checks that still need hands-on verification.
