#!/usr/bin/env python3
"""Little Buddy router — the ingestion, priority and failover tier.

Implements §2B and §2C of the Little Buddy Ecosystem Packet, adapted onto
the infrastructure that already exists rather than beside it. Admiral,
2026-08-05: "use existing infrastructure", "adapt", "software first".

**What already existed and is reused, not rebuilt:**

- `rich_voice.Provider` is already the packet's "synthesis abstraction" — a
  Protocol with one method. The cloud/local failover the packet asks for is
  therefore a Provider that wraps two Providers, and it plugs into the
  existing seam without inventing a second one.
- `RichVoiceEngine` already gives an immutable artifact cache, a daily USD
  and seconds budget, and reservation release on provider failure.

**What did not exist and is built here:** the priority queue with ducking,
the handshake status codes, the ring buffer, and the sink abstraction.

**One deliberate departure from the packet.** §2B specifies cloud-backed
neural voices with an 800ms failover and says nothing about cost. This repo
already decided that question — the voice engine never calls a paid provider
without an explicit render, and caps spend daily. So the router treats
budget exhaustion as a *failover condition*, exactly like a timeout, rather
than as an error. Running out of money sounds like the local voice, it does
not sound like silence or a crash.

Nothing here needs hardware. The sink is an interface; today it writes to a
file or nowhere, and an I2S DAC later is the same pipeline.
"""

from __future__ import annotations

import heapq
import json
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rich_voice import BudgetExceeded  # noqa: E402

# --- packet §3: interface contracts -----------------------------------------

READY = "READY"
BUFFERING = "BUFFERING"
DROPPED_QUEUE_FULL = "DROPPED_QUEUE_FULL"

#: §3 fallback protocol — primary must answer within this or we fail over.
PRIMARY_TIMEOUT_MS = 800

#: At or above this, a payload interrupts whatever is speaking. §2C calls
#: this ducking; here it is a hard preempt, because a critical fault that
#: waits politely for an ambient telemetry line to finish is not an alert.
DUCK_PRIORITY = 7

DEFAULT_CAPACITY = 32


class PayloadError(ValueError):
    pass


@dataclass(order=True)
class Payload:
    """The packet's JSON contract.

    Ordering is (-priority, timestamp, seq) so `heapq` yields the most
    urgent first and ties break by arrival — a plain max-heap on priority
    would reorder same-priority telemetry, which reads as glitching.
    """

    sort_key: tuple = field(init=False, repr=False)
    priority_level: int
    timestamp: int
    text_payload: str
    seq: int = 0

    def __post_init__(self) -> None:
        self.sort_key = (-self.priority_level, self.timestamp, self.seq)

    @classmethod
    def from_json(cls, raw: str | bytes | dict, seq: int = 0) -> "Payload":
        data = raw if isinstance(raw, dict) else json.loads(raw)
        missing = [k for k in ("timestamp", "priority_level", "text_payload")
                   if k not in data]
        if missing:
            raise PayloadError(f"missing required field(s): {', '.join(missing)}")
        text = data["text_payload"]
        if not isinstance(text, str) or not text.strip():
            raise PayloadError("text_payload must be a non-empty string")
        try:
            priority = int(data["priority_level"])
            timestamp = int(data["timestamp"])
        except (TypeError, ValueError) as error:
            raise PayloadError("priority_level and timestamp must be integers") from error
        if not 0 <= priority <= 10:
            raise PayloadError("priority_level must be within 0..10")
        return cls(priority_level=priority, timestamp=timestamp,
                   text_payload=text, seq=seq)

    @property
    def critical(self) -> bool:
        return self.priority_level >= DUCK_PRIORITY


# --- sinks ------------------------------------------------------------------

class Sink(Protocol):
    def write(self, pcm: bytes) -> None: ...
    def stop(self) -> None: ...


class NullSink:
    """Discards audio but records what it was given. The default, because a
    pipeline that can be exercised without a speaker is one that can be
    tested in CI and on a host with no DAC."""

    def __init__(self) -> None:
        self.written: list[bytes] = []
        self.stops = 0

    def write(self, pcm: bytes) -> None:
        self.written.append(pcm)

    def stop(self) -> None:
        self.stops += 1


class FileSink:
    """Appends raw PCM to a file — the 'listen to it later' sink."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, pcm: bytes) -> None:
        with self.path.open("ab") as handle:
            handle.write(pcm)

    def stop(self) -> None:
        pass


# --- §2B synthesis: failover over the existing Provider protocol ------------

class FailoverProvider:
    """Primary provider with a deadline and a local fallback.

    Satisfies `rich_voice.Provider`, so `RichVoiceEngine` can use it without
    knowing failover exists. Three conditions fail over, not one:

    - the primary raises;
    - the primary exceeds `timeout_ms`;
    - the primary reports the budget exhausted.

    The third is the adaptation. The packet only names timeouts, but this
    repo caps daily spend, and an exhausted budget is operationally the same
    event as an unreachable endpoint: the expensive voice is unavailable and
    the cheap one should speak.
    """

    def __init__(self, primary, fallback, *, timeout_ms: int = PRIMARY_TIMEOUT_MS):
        self.primary = primary
        self.fallback = fallback
        self.timeout_ms = timeout_ms
        self.failovers: list[str] = []

    def render_pcm(self, *, prompt: str, voice_name: str, model: str) -> bytes:
        if self.primary is None:
            self.failovers.append("no primary configured")
            return self.fallback.render_pcm(prompt=prompt, voice_name=voice_name,
                                            model=model)

        result: dict = {}

        def run() -> None:
            try:
                result["pcm"] = self.primary.render_pcm(
                    prompt=prompt, voice_name=voice_name, model=model)
            except BudgetExceeded as error:
                result["error"] = f"budget exhausted: {error}"
            except Exception as error:  # noqa: BLE001 - any primary failure fails over
                result["error"] = str(error)

        worker = threading.Thread(target=run, daemon=True)
        started = time.monotonic()
        worker.start()
        worker.join(self.timeout_ms / 1000)

        if worker.is_alive():
            # The thread is abandoned rather than killed — Python cannot kill
            # it. It is a daemon and its result is ignored, which is the
            # honest cost of a hard deadline on a blocking call.
            self.failovers.append(
                f"primary exceeded {self.timeout_ms}ms")
        elif "error" in result:
            self.failovers.append(result["error"])
        elif "pcm" in result:
            return result["pcm"]
        else:
            self.failovers.append("primary returned nothing")

        _ = time.monotonic() - started
        return self.fallback.render_pcm(prompt=prompt, voice_name=voice_name,
                                        model=model)


# --- §2C router -------------------------------------------------------------

@dataclass
class Spoken:
    payload: Payload
    status: str
    pcm_bytes: int
    ducked: bool = False
    failed_over: bool = False


class BuddyRouter:
    """Priority queue, ducking, capacity and flow control in front of a sink.

    Deliberately synchronous and single-threaded: the ordering rules are the
    thing worth being sure about, and they are far easier to prove without a
    scheduler in the way. A caller that wants a background pump can drive
    `pump()` from its own thread.
    """

    def __init__(self, synth, sink: Sink | None = None, *,
                 capacity: int = DEFAULT_CAPACITY):
        self.synth = synth
        self.sink = sink or NullSink()
        self.capacity = capacity
        self._heap: list[Payload] = []
        self._seq = 0
        self.spoken: list[Spoken] = []
        self.dropped: list[Payload] = []

    # -- ingestion --

    def submit(self, raw) -> dict:
        """§3 audio handshake. Returns a status *before* execution."""
        try:
            self._seq += 1
            payload = (raw if isinstance(raw, Payload)
                       else Payload.from_json(raw, seq=self._seq))
        except PayloadError as error:
            return {"status": "REJECTED", "error": str(error)}

        if len(self._heap) >= self.capacity:
            # Critical traffic is never dropped for want of room: it evicts
            # the least urgent thing waiting. Dropping an alert because the
            # queue is full of ambient chatter is the failure this guards.
            if payload.critical and self._evict_lowest():
                pass
            else:
                self.dropped.append(payload)
                return {"status": DROPPED_QUEUE_FULL, "queued": len(self._heap)}

        heapq.heappush(self._heap, payload)
        status = READY if len(self._heap) == 1 else BUFFERING
        return {"status": status, "queued": len(self._heap),
                "critical": payload.critical}

    def _evict_lowest(self) -> bool:
        if not self._heap:
            return False
        victim = max(self._heap, key=lambda p: p.sort_key)
        if victim.critical:
            return False
        self._heap.remove(victim)
        heapq.heapify(self._heap)
        self.dropped.append(victim)
        return True

    # -- playback --

    def pump(self, limit: int | None = None) -> list[Spoken]:
        """Speak queued payloads, most urgent first."""
        out = []
        while self._heap and (limit is None or len(out) < limit):
            payload = heapq.heappop(self._heap)
            ducked = self._duck_if_needed(payload)
            before = len(getattr(self.synth, "failovers", []))
            pcm = self.synth.render_pcm(
                prompt=payload.text_payload, voice_name="buddy", model="local")
            failed_over = len(getattr(self.synth, "failovers", [])) > before
            self.sink.write(pcm)
            record = Spoken(payload=payload, status=READY, pcm_bytes=len(pcm),
                            ducked=ducked, failed_over=failed_over)
            self.spoken.append(record)
            out.append(record)
        return out

    def _duck_if_needed(self, payload: Payload) -> bool:
        """A critical payload cuts off whatever is sounding."""
        if payload.critical and self.spoken:
            self.sink.stop()
            return True
        return False

    @property
    def queued(self) -> int:
        return len(self._heap)

    def status(self) -> dict:
        return {
            "queued": self.queued,
            "capacity": self.capacity,
            "spoken": len(self.spoken),
            "dropped": len(self.dropped),
            "failovers": list(getattr(self.synth, "failovers", [])),
            "duck_priority": DUCK_PRIORITY,
            "primary_timeout_ms": PRIMARY_TIMEOUT_MS,
        }
