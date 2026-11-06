import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from desktop_toolkit.backup import (
    collect,
    create_backup,
    require_mount,
    restore,
    verify,
)


class Backups(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        (self.home / ".config").mkdir()
        (self.home / ".config/example").write_text("original settings\n")
        self.dest = self.root / "backup"
        self.dest.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def backup(self):
        with patch("desktop_toolkit.backup.require_mount"):
            return create_backup(
                self.home, [".config/example", ".config/optional"], self.dest, "test"
            )

    def test_roundtrip_and_integrity(self):
        archive = self.backup()
        manifest = verify(archive)
        self.assertEqual(manifest["skipped_missing"], [".config/optional"])
        self.assertEqual(archive.stat().st_mode & 0o777, 0o600)
        target = self.root / "staged"
        restore(archive, target)
        self.assertEqual(
            (target / ".config/example").read_bytes(),
            (self.home / ".config/example").read_bytes(),
        )
        self.assertEqual((target / ".config/example").stat().st_mode & 0o777, 0o600)

    def test_mount_mismatch_and_missing_uuid(self):
        with patch(
            "desktop_toolkit.backup.subprocess.check_output", return_value="different\n"
        ):
            with self.assertRaises(ValueError):
                require_mount(self.dest, "expected")
        with self.assertRaises(ValueError):
            require_mount(self.dest, "")

    def test_no_live_overwrite(self):
        with self.assertRaises(ValueError):
            restore(self.backup(), self.home)
        self.assertEqual(
            (self.home / ".config/example").read_text(), "original settings\n"
        )

    def test_reject_symlinks_and_parent_traversal(self):
        (self.home / "link").symlink_to(self.home / ".config", target_is_directory=True)
        for path in ["../elsewhere", "/etc/passwd", "link/example"]:
            with self.assertRaises(ValueError):
                collect(self.home, [path])

    def malicious(self, name, data=b"changed", expected=b"original"):
        output = self.root / "malicious.tar.gz"
        manifest = {
            "version": 1,
            "files": {
                name: {
                    "size": len(expected),
                    "sha256": hashlib.sha256(expected).hexdigest(),
                }
            },
        }
        with tarfile.open(output, "w:gz") as tar:
            for n, value in [
                ("manifest.json", json.dumps(manifest).encode()),
                (name, data),
            ]:
                member = tarfile.TarInfo(n)
                member.size = len(value)
                tar.addfile(member, io.BytesIO(value))
        return output

    def test_reject_tampered_archives(self):
        with self.assertRaises(ValueError):
            verify(self.malicious(".config/example"))

    def test_reject_archive_path_traversal(self):
        with self.assertRaises(ValueError):
            restore(self.malicious("../escape"), self.root / "out")
        self.assertFalse((self.root / "out").exists())

    def test_dry_run_does_not_write(self):
        with patch("desktop_toolkit.backup.require_mount"):
            result = create_backup(
                self.home, [".config/example"], self.dest, "test", True
            )
        self.assertIn(".config/example", result["files"])
        self.assertEqual(list(self.dest.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
