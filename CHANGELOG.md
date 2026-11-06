# Changelog

## 0.1.0 — 2026-11-06

Initial public implementation. See README.md for scope, test commands, provenance and outstanding live/device checks.

## Verification — 2026-11-06

12 unittest cases passed on Python 3.14: selected-file round trip, checksum tampering, traversal/symlink rejection, mount mismatch, staging-only restore, mocked audio and launcher supervision. Wheel installation and all three command help entrypoints were checked in an isolated virtual environment. No backup was taken from a real home directory by this release check. Audio routing and Rofi window behavior require a graphical-session check on the target machine.
