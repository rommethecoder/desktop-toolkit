"""Selected desktop settings backup, verification and staged restore."""

from __future__ import annotations
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import tarfile
import tempfile
from datetime import datetime, timezone

MAX_BYTES = 512 * 1024 * 1024
MANIFEST = "manifest.json"


def relative_name(value):
    p = PurePosixPath(value)
    if (
        not value
        or p.is_absolute()
        or ".." in p.parts
        or str(p) in (".", MANIFEST)
        or "\\" in value
    ):
        raise ValueError(f"Unsafe relative path: {value!r}")
    return str(p)


def collect(home, paths):
    """Do not follow symlinks, including intermediate path components."""
    home = Path(home).resolve(strict=True)
    found, missing = {}, []
    for value in paths:
        rel = relative_name(value)
        source = home / rel
        for parent in [source, *source.parents]:
            if parent == home:
                break
            if parent.is_symlink():
                raise ValueError(f"Symlink not allowed: {rel}")
        if not source.exists():
            missing.append(rel)
            continue
        candidates = (
            [source, *sorted(source.rglob("*"))] if source.is_dir() else [source]
        )
        for candidate in candidates:
            name = candidate.relative_to(home).as_posix()
            mode = candidate.lstat().st_mode
            if stat.S_ISLNK(mode) or not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
                raise ValueError(
                    f"Only regular files/directories can be backed up: {name}"
                )
            if candidate.is_file():
                found[name] = candidate
    if not found:
        raise ValueError("None of the selected paths contains files.")
    return found, missing


def require_mount(destination, expected_uuid):
    if not expected_uuid or not Path(destination).is_dir():
        raise ValueError(
            "Destination must exist and mount_uuid must be explicitly configured."
        )
    actual = subprocess.check_output(
        ["findmnt", "-n", "-o", "UUID", "-T", str(Path(destination).resolve())],
        text=True,
    ).strip()
    if actual != expected_uuid:
        raise ValueError("Destination filesystem UUID does not match; backup aborted.")


def create_backup(home, paths, destination, expected_uuid, dry_run=False):
    files, missing = collect(home, paths)
    require_mount(destination, expected_uuid)
    report = {"version": 1, "files": {}, "skipped_missing": missing}
    content = {}
    remaining = MAX_BYTES
    for name, path in files.items():
        if path.stat().st_size > remaining:
            raise ValueError("Selected files exceed the 512 MiB limit.")
        with path.open("rb") as source:
            data = source.read(remaining + 1)
        if len(data) > remaining:
            raise ValueError("Selected files exceed the 512 MiB limit.")
        remaining -= len(data)
        content[name] = data
        report["files"][name] = {
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "mode": stat.S_IMODE(path.stat().st_mode) & 0o777,
        }
    if sum(len(data) for data in content.values()) > MAX_BYTES:
        raise ValueError("Selected files exceed the 512 MiB limit.")
    if dry_run:
        return report
    report["created_at"] = datetime.now(timezone.utc).isoformat()
    destination = Path(destination).resolve()
    handle, temporary = tempfile.mkstemp(
        prefix=".desktop-backup-", suffix=".tmp", dir=destination
    )
    final = destination / (
        "desktop-settings-"
        + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        + "-"
        + os.urandom(3).hex()
        + ".tar.gz"
    )
    try:
        with (
            os.fdopen(handle, "wb") as output,
            tarfile.open(fileobj=output, mode="w:gz") as archive,
        ):
            for name, data in [
                (MANIFEST, json.dumps(report, sort_keys=True).encode()),
                *content.items(),
            ]:
                member = tarfile.TarInfo(name)
                member.size = len(data)
                member.mode = (
                    0o600  # settings archives are private, regardless of source mode
                )
                archive.addfile(member, io.BytesIO(data))
        verify(temporary)
        os.rename(temporary, final)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return final


def verify(archive_path):
    with tarfile.open(archive_path, "r:gz") as archive:
        members = archive.getmembers()
        names = [m.name for m in members]
        if len(names) != len(set(names)) or names.count(MANIFEST) != 1:
            raise ValueError("Duplicate members or missing manifest.")
        if (
            any(not m.isfile() for m in members)
            or sum(m.size for m in members) > MAX_BYTES + 4 * 1024 * 1024
        ):
            raise ValueError("Archive contains links, non-files, or excessive data.")
        if archive.getmember(MANIFEST).size > 4 * 1024 * 1024:
            raise ValueError("Manifest too large.")
        raw = archive.extractfile(MANIFEST).read()
        if len(raw) > 4 * 1024 * 1024:
            raise ValueError("Manifest too large.")
        manifest = json.loads(raw)
        if manifest.get("version") != 1 or not isinstance(manifest.get("files"), dict):
            raise ValueError("Unsupported manifest.")
        expected = manifest["files"]
        if set(names) != {MANIFEST, *expected}:
            raise ValueError("Archive and manifest members disagree.")
        for name, metadata in expected.items():
            relative_name(name)
            if any(
                str(parent) in expected
                for parent in PurePosixPath(name).parents
                if str(parent) != "."
            ):
                raise ValueError("Archive has conflicting file and directory names.")
            data = archive.extractfile(name).read()
            if (
                len(data) != metadata["size"]
                or hashlib.sha256(data).hexdigest() != metadata["sha256"]
            ):
                raise ValueError(f"Integrity check failed: {name}")
        return manifest


def restore(archive_path, target):
    """Restore only into a new staging directory; never overwrite the live desktop."""
    manifest = verify(archive_path)
    target = Path(target)
    if target.exists() or target.is_symlink():
        raise ValueError(
            "Restore target must not already exist. Choose a new staging directory."
        )
    parent = target.parent.resolve(strict=True)
    target = parent / target.name
    if target.name in (".", ".."):
        raise ValueError("Choose a named staging directory.")
    # Exclusive mkdir also rejects a target created between validation and extraction.
    target.mkdir(mode=0o700)
    with tarfile.open(archive_path, "r:gz") as archive:
        for name in manifest["files"]:
            path = target / name
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            data = archive.extractfile(name).read()
            expected = manifest["files"][name]
            if (
                len(data) != expected["size"]
                or hashlib.sha256(data).hexdigest() != expected["sha256"]
            ):
                raise ValueError(
                    "Archive changed during restore; staging is incomplete."
                )
            with path.open("xb") as output:
                output.write(data)
            path.chmod(0o600)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    backup = sub.add_parser("backup")
    backup.add_argument("--config", required=True, type=Path)
    backup.add_argument("--dry-run", action="store_true")
    check = sub.add_parser("verify")
    check.add_argument("archive", type=Path)
    stage = sub.add_parser("restore")
    stage.add_argument("archive", type=Path)
    stage.add_argument("--target", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == "backup":
            config = json.loads(args.config.read_text())
            result = create_backup(
                Path.home(),
                config["paths"],
                Path(os.path.expandvars(config["destination"])).expanduser(),
                config["mount_uuid"],
                args.dry_run,
            )
        elif args.command == "verify":
            result = verify(args.archive)
        else:
            result = restore(args.archive, args.target)
        print(json.dumps(result, indent=2) if isinstance(result, dict) else result)
    except (
        OSError,
        ValueError,
        KeyError,
        tarfile.TarError,
        subprocess.SubprocessError,
    ) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
