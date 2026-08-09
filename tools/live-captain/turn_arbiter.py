"""FIFO admission for Live Captain turns before context is compiled."""

from __future__ import annotations

import threading


class TurnArbiter:
    def __init__(self):
        self._condition = threading.Condition()
        self._next_ticket = 1
        self._serving = 1
        self._active: int | None = None

    def acquire(self) -> int:
        with self._condition:
            ticket = self._next_ticket
            self._next_ticket += 1
            while ticket != self._serving:
                self._condition.wait()
            self._active = ticket
            return ticket

    def release(self, ticket: int) -> None:
        with self._condition:
            if self._active != ticket:
                return
            self._active = None
            self._serving += 1
            self._condition.notify_all()

    def status(self) -> dict:
        with self._condition:
            return {
                "active_ticket": self._active,
                "queued": self._next_ticket - self._serving - (1 if self._active else 0),
                "next_ticket": self._next_ticket,
            }
