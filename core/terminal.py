"""
core/terminal.py — PTY Manager for the Direct Shell Web-CLI.

Uses os.forkpty() to spawn a /bin/bash process attached to a pseudo-terminal.
IMPORTANT: This module requires a UNIX/Linux environment. It will NOT work on Windows.
"""

import os
import signal
import struct
import fcntl
import termios
import asyncio
from typing import Optional


# Default workspace directory for the shell session
WORKSPACE_DIR = os.path.expanduser("~/auto-tensor/workspace")


class PtyManager:
    """
    Manages a single /bin/bash process attached to a pseudo-terminal (PTY).

    Lifecycle:
        1. Call spawn() to fork a bash process.
        2. Use read() / write() to stream data between the PTY and a WebSocket.
        3. Call resize(rows, cols) whenever the terminal dimensions change.
        4. Call kill() on WebSocket disconnect to clean up the child process.
    """

    def __init__(self):
        self.master_fd: Optional[int] = None
        self.pid: Optional[int] = None
        self.active: bool = False

    def spawn(self) -> None:
        """Fork a bash process inside a PTY, starting in the workspace directory."""
        if self.active:
            return

        # Ensure the workspace directory exists
        if not os.path.isdir(WORKSPACE_DIR):
            try:
                os.makedirs(WORKSPACE_DIR, exist_ok=True)
            except OSError:
                pass  # Fall back to home dir if creation fails

        start_dir = WORKSPACE_DIR if os.path.isdir(WORKSPACE_DIR) else os.path.expanduser("~")

        # os.forkpty() returns (pid, master_fd) in the parent process
        # and (0, ...) in the child process
        pid, master_fd = os.forkpty()

        if pid == 0:
            # --- Child process ---
            # Change into the workspace directory
            try:
                os.chdir(start_dir)
            except OSError:
                os.chdir(os.path.expanduser("~"))

            # Set a clean TERM environment
            env = os.environ.copy()
            env["TERM"] = "xterm-256color"
            env["HOME"] = os.path.expanduser("~")

            # Replace the child process with /bin/bash
            os.execvpe("/bin/bash", ["/bin/bash"], env)

        else:
            # --- Parent process ---
            self.pid = pid
            self.master_fd = master_fd
            self.active = True

    def read(self, n: int = 1024) -> bytes:
        """
        Read up to n bytes from the PTY master FD.
        Returns empty bytes if the PTY is closed or an OS error occurs.
        """
        if not self.active or self.master_fd is None:
            return b""
        try:
            return os.read(self.master_fd, n)
        except OSError:
            self.active = False
            return b""

    def write(self, data: bytes) -> None:
        """Write raw bytes to the PTY (i.e., to bash's stdin)."""
        if not self.active or self.master_fd is None:
            return
        try:
            os.write(self.master_fd, data)
        except OSError:
            self.active = False

    def resize(self, rows: int, cols: int) -> None:
        """
        Notify the PTY of a terminal resize event.
        Uses the TIOCSWINSZ ioctl to set the window size.
        """
        if not self.active or self.master_fd is None:
            return
        try:
            # struct winsize: unsigned short ws_row, ws_col, ws_xpixel, ws_ypixel
            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)
        except OSError:
            pass  # Non-fatal — ignore if the FD is not a TTY yet

    def kill(self) -> None:
        """Terminate the bash child process and close the master FD."""
        self.active = False

        if self.pid:
            try:
                os.kill(self.pid, signal.SIGTERM)
                os.waitpid(self.pid, os.WNOHANG)
            except (OSError, ChildProcessError):
                pass
            self.pid = None

        if self.master_fd is not None:
            try:
                os.close(self.master_fd)
            except OSError:
                pass
            self.master_fd = None
