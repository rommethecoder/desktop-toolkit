# How my desktop backup routine became a reusable toolkit

I wanted a way to keep the parts of my CachyOS desktop I had spent time changing. A system rollback could help with a bad update, but my separate home directory still needed its own backup. The original routine saved selected desktop settings to a different drive before I updated packages.

The public toolkit takes that idea and removes the machine-specific paths and drive identity. You choose the files and destination. Before writing anything, it checks that the destination is the filesystem you expected. Each archive includes file hashes so a later verification can detect changed contents.

Recovery was the part I wanted to be careful about. The restore command writes into a new staging directory, so reviewing a backup does not overwrite the desktop I am currently using. The toolkit also includes two small helpers from the same setup: switching the default audio output and toggling a Rofi launcher managed by its own supervisor.

The first public release, v0.1.0, was published on November 6, 2026. Twelve tests passed locally and in GitHub Actions. They cover backup/restore, checksums, unsafe paths, mount mismatches, and mocked audio/launcher behavior. Wheel installation and command entrypoints were also checked. The graphical helpers still need hands-on testing on the machine where someone wants to use them.

This is a selected-settings toolkit. It does not encrypt archives or replace a full backup plan. My private machine recovery setup now uses a separate encrypted backup as well; its credentials and personal configuration do not belong in this public project.

## Keeping this history useful

This is a retrospective of the work that actually led to the first release, not a reconstructed commit sequence. Further changes should be committed as they happen, with plain-language messages explaining the problem, the decision and the checks that were run. Source and documentation were prepared with AI assistance; the verification limits above remain part of the project history.
