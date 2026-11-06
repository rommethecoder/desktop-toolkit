import fcntl
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from desktop_toolkit import rofi


class Rofi(unittest.TestCase):
    def test_managed_launcher_supervisor(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.dict(os.environ, {"XDG_RUNTIME_DIR": tmp}),
            patch("desktop_toolkit.rofi.shutil.which", return_value="/usr/bin/rofi"),
            patch("desktop_toolkit.rofi.subprocess.Popen") as child,
        ):
            child.return_value.pid = 1234
            rofi.main([])
            child.assert_called_once_with(["rofi", "-show", "drun"])
            child.return_value.wait.assert_called_once()
            self.assertEqual((Path(tmp) / "desktop-toolkit-rofi.lock").read_text(), "")

    def test_private_runtime_required(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.dict(os.environ, {"XDG_RUNTIME_DIR": tmp}),
        ):
            Path(tmp).chmod(0o755)
            with self.assertRaises(SystemExit):
                rofi.main([])

    def test_locked_without_valid_pid_does_not_kill_other_windows(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.dict(os.environ, {"XDG_RUNTIME_DIR": tmp}),
            patch("desktop_toolkit.rofi.shutil.which", return_value="/usr/bin/rofi"),
            patch("desktop_toolkit.rofi.os.kill") as kill,
        ):
            with (Path(tmp) / "desktop-toolkit-rofi.lock").open("w+") as lock:
                lock.write("not-a-pid")
                lock.flush()
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                rofi.main([])
                kill.assert_not_called()
