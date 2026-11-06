"""Toggle a launcher instance owned by this utility, without killing other Rofi windows."""

import argparse
import fcntl
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess


def main(argv=None):
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    runtime = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
    status = runtime.stat()
    if status.st_uid != os.getuid() or status.st_mode & 0o077:
        raise SystemExit("XDG_RUNTIME_DIR must be owned by you and private.")
    if not shutil.which("rofi"):
        raise SystemExit("Install Rofi first.")
    path = runtime / "desktop-toolkit-rofi.lock"
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "r+") as lock:
        metadata = os.fstat(lock.fileno())
        if metadata.st_uid != os.getuid() or not stat.S_ISREG(metadata.st_mode):
            raise SystemExit("Invalid launcher lock.")
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            pid = lock.read().strip()
            if pid.isdigit():
                proc = Path("/proc") / pid
                try:
                    cmd = (proc / "cmdline").read_bytes().split(b"\0")
                    if (
                        proc.stat().st_uid == os.getuid()
                        and b"rofi" in Path(os.fsdecode(cmd[0])).name.encode()
                        and b"-show" in cmd
                        and b"drun" in cmd
                    ):
                        os.kill(int(pid), signal.SIGTERM)
                except (FileNotFoundError, ProcessLookupError):
                    pass
            return
        # flock remains held by the supervisor while its child launcher runs.
        child = subprocess.Popen(["rofi", "-show", "drun"])
        lock.seek(0)
        lock.truncate()
        lock.write(str(child.pid))
        lock.flush()
        try:
            child.wait()
        finally:
            lock.seek(0)
            lock.truncate()
            lock.flush()


if __name__ == "__main__":
    main()
