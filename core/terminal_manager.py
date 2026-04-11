"""
core/terminal_manager.py — Persistent PTY Session Manager

Decouples the bash process lifecycle from the WebSocket connection lifecycle.
A TerminalSession outlives individual browser connections; clients may
re-attach and receive a replay of buffered output.

Environment variables:
  TERMINAL_SESSION_TTL_HOURS   Float, default 4.0 — how long an orphaned
                               (no connected clients) session is kept alive.
  TERMINAL_BUFFER_SIZE         Int, default 200 — max output chunks retained.
"""

import asyncio
import logging
import os
import time
from collections import deque
from typing import Dict, Optional, Set

from fastapi import WebSocket

from core.terminal import PtyManager

logger = logging.getLogger("terminal_manager")

# ---------------------------------------------------------------------------
# Configuration (overridable via env)
# ---------------------------------------------------------------------------
_TTL_HOURS: float = float(os.getenv("TERMINAL_SESSION_TTL_HOURS", "4"))
_BUFFER_SIZE: int = int(os.getenv("TERMINAL_BUFFER_SIZE", "200"))
_GC_INTERVAL_SECONDS: int = 60  # how often the GC loop wakes up


# ---------------------------------------------------------------------------
# TerminalSession
# ---------------------------------------------------------------------------
class TerminalSession:
    """
    One persistent bash session.

    Attributes:
        session_id      Unique key (e.g. 'trevor-main').
        pty             PtyManager that owns the forked bash process.
        output_buffer   Circular buffer of raw bytes chunks written by bash.
        active_clients  The set of currently connected WebSocket objects.
        last_client_at  Epoch timestamp of the most recent client disconnect.
        _reader_task    The single asyncio Task that drains the PTY and
                        broadcasts to all active_clients.
    """

    def __init__(self, session_id: str) -> None:
        self.session_id: str = session_id
        self.pty: PtyManager = PtyManager()
        self.output_buffer: deque[bytes] = deque(maxlen=_BUFFER_SIZE)
        self.active_clients: Set[WebSocket] = set()
        self.last_client_at: float = time.time()
        self._reader_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def spawn(self) -> None:
        """Fork the bash process (no-op if already running)."""
        if not self.pty.active:
            self.pty.spawn()
            logger.info("[%s] PTY spawned (PID %s)", self.session_id, self.pty.pid)

    async def start_reader(self) -> None:
        """
        Start the background PTY→broadcast loop if not already running.
        This task is shared across all attached WebSocket clients.
        """
        if self._reader_task and not self._reader_task.done():
            return  # already running

        self._reader_task = asyncio.create_task(
            self._reader_loop(), name=f"pty-reader-{self.session_id}"
        )

    async def _reader_loop(self) -> None:
        """
        Continuously drain PTY output, append to buffer, and broadcast
        to every currently connected client.
        """
        loop = asyncio.get_event_loop()
        logger.info("[%s] Reader loop started", self.session_id)

        while self.pty.active:
            try:
                data: bytes = await loop.run_in_executor(None, self.pty.read, 4096)
            except Exception as exc:
                logger.warning("[%s] PTY read error: %s", self.session_id, exc)
                break

            if not data:
                # PTY closed (bash exited)
                logger.info("[%s] PTY EOF — bash exited", self.session_id)
                break

            # Persist to buffer
            self.output_buffer.append(data)

            # Broadcast to all attached clients (best-effort; dead sockets drop)
            dead: Set[WebSocket] = set()
            for ws in list(self.active_clients):
                try:
                    await ws.send_bytes(data)
                except Exception:
                    dead.add(ws)

            for ws in dead:
                self.active_clients.discard(ws)

        # PTY exited — mark as inactive so the manager can GC it
        self.pty.active = False
        logger.info("[%s] Reader loop finished", self.session_id)

    def clear_buffer(self) -> None:
        """Flush the output buffer (does NOT affect the running shell)."""
        self.output_buffer.clear()
        logger.info("[%s] Output buffer cleared", self.session_id)

    def is_alive(self) -> bool:
        """Return True if the underlying bash process is still running."""
        return self.pty.active and self.pty.is_alive()

    def kill(self) -> None:
        """Terminate the bash process and cancel the reader task."""
        if self._reader_task and not self._reader_task.done():
            self._reader_task.cancel()
        self.pty.kill()
        self.active_clients.clear()
        logger.info("[%s] Session killed", self.session_id)


# ---------------------------------------------------------------------------
# TerminalManager  (global singleton)
# ---------------------------------------------------------------------------
class TerminalManager:
    """
    Global registry of TerminalSession objects.

    Usage:
        session = await terminal_manager.get_or_create("trevor-main")
    """

    def __init__(self) -> None:
        self._sessions: Dict[str, TerminalSession] = {}
        self._gc_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def get_or_create(self, session_id: str) -> TerminalSession:
        """
        Return an existing live session or spawn a fresh one.
        Also ensures the PTY reader loop is running.
        """
        session = self._sessions.get(session_id)

        if session is None or not session.is_alive():
            # Clean up any dead remnant
            if session is not None:
                session.kill()

            session = TerminalSession(session_id)
            session.spawn()
            self._sessions[session_id] = session
            logger.info("[%s] New session created", session_id)
        else:
            logger.info("[%s] Existing session re-attached", session_id)

        # Ensure the single shared reader loop is running
        await session.start_reader()

        return session

    def get(self, session_id: str) -> Optional[TerminalSession]:
        """Return an existing session or None (no side effects)."""
        return self._sessions.get(session_id)

    def close_session(self, session_id: str) -> None:
        """Forcibly terminate and remove a session."""
        session = self._sessions.pop(session_id, None)
        if session:
            session.kill()

    # ------------------------------------------------------------------
    # Garbage Collection
    # ------------------------------------------------------------------
    async def start_gc(self) -> None:
        """Launch the background GC coroutine (call once on app startup)."""
        if self._gc_task is None or self._gc_task.done():
            self._gc_task = asyncio.create_task(
                self._gc_loop(), name="terminal-manager-gc"
            )

    async def _gc_loop(self) -> None:
        """
        Periodically prune sessions that:
          - have no connected clients AND
          - have been idle for longer than TERMINAL_SESSION_TTL_HOURS, OR
          - whose PTY process has already exited.
        """
        ttl_seconds = _TTL_HOURS * 3600
        logger.info(
            "GC loop started — TTL=%.1f h, interval=%d s",
            _TTL_HOURS,
            _GC_INTERVAL_SECONDS,
        )

        while True:
            await asyncio.sleep(_GC_INTERVAL_SECONDS)

            now = time.time()
            to_prune = []

            for sid, session in list(self._sessions.items()):
                dead_process = not session.is_alive()
                orphaned = (
                    len(session.active_clients) == 0
                    and (now - session.last_client_at) > ttl_seconds
                )
                if dead_process or orphaned:
                    to_prune.append(sid)

            for sid in to_prune:
                logger.info("GC: pruning session '%s'", sid)
                self.close_session(sid)


# ---------------------------------------------------------------------------
# Module-level singleton — import this in api.py
# ---------------------------------------------------------------------------
terminal_manager = TerminalManager()
