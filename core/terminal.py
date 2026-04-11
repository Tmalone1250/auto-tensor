import os
import signal
from typing import Optional
from ptyprocess import PtyProcess

# Default workspace directory for the shell session
WORKSPACE_DIR = os.path.expanduser("~/auto-tensor/workspace")

class PtyManager:
    """
    Manages a single /bin/bash process attached to a pseudo-terminal (PTY)
    using the ptyprocess library for better stability.
    """

    def __init__(self):
        self.process: Optional[PtyProcess] = None
        self.active: bool = False

    @property
    def pid(self) -> Optional[int]:
        return self.process.pid if self.process else None

    def spawn(self) -> None:
        """Spawn a bash process inside a PTY, starting in the workspace directory."""
        if self.active and self.process and self.process.isalive():
            return

        if not os.path.isdir(WORKSPACE_DIR):
            try:
                os.makedirs(WORKSPACE_DIR, exist_ok=True)
            except OSError:
                pass

        start_dir = WORKSPACE_DIR if os.path.isdir(WORKSPACE_DIR) else os.path.expanduser("~")
        
        env = os.environ.copy()
        env["TERM"] = "xterm-256color"
        env["HOME"] = os.path.expanduser("~")

        self.process = PtyProcess.spawn(
            ["/bin/bash"],
            cwd=start_dir,
            env=env
        )
        self.active = True

    def read(self, n: int = 4096) -> bytes:
        """Read up to n bytes from the PTY."""
        if not self.active or not self.process:
            return b""
        try:
            return self.process.read(n)
        except EOFError:
            self.active = False
            return b""
        except Exception:
            self.active = False
            return b""

    def write(self, data: bytes) -> None:
        """Write raw bytes to the PTY."""
        if not self.active or not self.process:
            return
        try:
            self.process.write(data)
            self.process.flush()
        except Exception:
            self.active = False

    def resize(self, rows: int, cols: int) -> None:
        """Notify the PTY of a terminal resize event."""
        if not self.active or not self.process:
            return
        try:
            self.process.setwinsize(rows, cols)
        except Exception:
            pass

    def is_alive(self) -> bool:
        """Return True if the bash process is still running."""
        return self.process is not None and self.process.isalive()

    def kill(self) -> None:
        """Terminate the bash child process."""
        self.active = False
        if self.process:
            try:
                self.process.terminate(force=True)
            except Exception:
                pass
            self.process = None
