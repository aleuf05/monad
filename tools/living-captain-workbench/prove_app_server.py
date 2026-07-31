#!/usr/bin/env python3
"""One-turn, read-only proof that the local Codex app-server daemon is callable."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import struct
import time
from datetime import UTC, datetime
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
SOCKET = Path.home() / ".codex" / "app-server-control" / "app-server-control.sock"
RECEIPT = REPO / "data" / "living-captain-workbench" / "app-server-proof.json"


class UnixWebSocket:
    def __init__(self, path: Path):
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.settimeout(120)
        self.socket.connect(str(path))
        key = base64.b64encode(os.urandom(16)).decode()
        request = (
            "GET / HTTP/1.1\r\nHost: localhost\r\nUpgrade: websocket\r\n"
            f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\nOrigin: http://localhost\r\n\r\n"
        )
        self.socket.sendall(request.encode())
        response = self._until(b"\r\n\r\n")
        if not response.startswith(b"HTTP/1.1 101"):
            raise RuntimeError(response.decode(errors="replace"))
        expected = base64.b64encode(
            hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()
        ).decode()
        if f"Sec-WebSocket-Accept: {expected}".lower() not in response.decode().lower():
            raise RuntimeError("invalid WebSocket handshake")

    def _until(self, marker: bytes) -> bytes:
        data = b""
        while marker not in data:
            data += self.socket.recv(4096)
        return data

    def send_json(self, value: dict) -> None:
        payload = json.dumps(value, separators=(",", ":")).encode()
        mask = os.urandom(4)
        length = len(payload)
        header = bytearray([0x81])
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.extend([0x80 | 126])
            header.extend(struct.pack("!H", length))
        else:
            header.extend([0x80 | 127])
            header.extend(struct.pack("!Q", length))
        masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        self.socket.sendall(bytes(header) + mask + masked)

    def receive_json(self) -> dict:
        while True:
            first, second = self._read(2)
            opcode, length = first & 0x0F, second & 0x7F
            if length == 126:
                length = struct.unpack("!H", self._read(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self._read(8))[0]
            payload = self._read(length)
            if opcode == 0x9:
                self.socket.sendall(bytes([0x8A, len(payload)]) + payload)
                continue
            if opcode == 0x8:
                raise RuntimeError("daemon closed WebSocket")
            if opcode == 0x1:
                return json.loads(payload)

    def _read(self, length: int) -> bytes:
        data = b""
        while len(data) < length:
            chunk = self.socket.recv(length - len(data))
            if not chunk:
                raise RuntimeError("daemon socket closed")
            data += chunk
        return data

    def close(self) -> None:
        self.socket.close()


def main() -> int:
    started = time.monotonic()
    client = UnixWebSocket(SOCKET)
    client.send_json({
        "method": "initialize", "id": 1,
        "params": {"clientInfo": {
            "name": "monad_captain_proof", "title": "Monad Captain Proof", "version": "0.1.0",
        }},
    })
    thread_id = None
    final_text = None
    events = []
    try:
        while time.monotonic() - started < 120:
            message = client.receive_json()
            method = message.get("method")
            if method:
                events.append(method)
            if message.get("id") == 1:
                if "error" in message:
                    raise RuntimeError(str(message["error"]))
                client.send_json({"method": "initialized", "params": {}})
                client.send_json({
                    "method": "thread/start", "id": 2,
                    "params": {
                        "cwd": str(REPO), "sandbox": "read-only",
                        "approvalPolicy": "never", "ephemeral": True,
                        "baseInstructions": (
                            "This is a bounded connectivity proof. Do not call tools, read files, "
                            "modify anything, or add explanation. Reply with exactly CAPTAIN_DAEMON_ACK."
                        ),
                    },
                })
            elif message.get("id") == 2:
                if "error" in message:
                    raise RuntimeError(str(message["error"]))
                thread_id = message["result"]["thread"]["id"]
                client.send_json({
                    "method": "turn/start", "id": 3,
                    "params": {
                        "threadId": thread_id,
                        "input": [{"type": "text", "text": "Acknowledge this local job."}],
                    },
                })
            elif method == "item/completed":
                item = message.get("params", {}).get("item", {})
                if item.get("type") == "agentMessage":
                    final_text = item.get("text")
            elif method == "turn/completed":
                status = message.get("params", {}).get("turn", {}).get("status")
                if status != "completed":
                    raise RuntimeError(f"turn ended with status {status}")
                break
        else:
            raise TimeoutError("app-server proof timed out")
    finally:
        client.close()

    receipt = {
        "schema": "monad.codexAppServerProof.v0.1",
        "observed_at": datetime.now(UTC).isoformat(),
        "transport": "WebSocket over local Unix control socket",
        "thread_id": thread_id,
        "sandbox": "read-only",
        "approval_policy": "never",
        "response": final_text,
        "expected_response": "CAPTAIN_DAEMON_ACK",
        "verified": final_text == "CAPTAIN_DAEMON_ACK",
        "elapsed_ms": round((time.monotonic() - started) * 1000),
        "event_methods": sorted(set(events)),
    }
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))
    return 0 if receipt["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
