#!/usr/bin/env python3
"""Create the protected Chat Captain web-auth environment file.

Copied from tools/living-captain/configure_web_auth.py -- the scrypt
verifier + session-secret provisioning is schema-agnostic and reused
wholesale, just pointed at a distinct secrets file and env-var prefix.
"""

from __future__ import annotations

import getpass
import hashlib
import os
import secrets
import sys
from pathlib import Path


OUTPUT = Path("/home/cgl/.config/monad/chat-captain-web.env")


def main() -> int:
    first = getpass.getpass("Choose Chat Captain password: ")
    second = getpass.getpass("Confirm Chat Captain password: ")
    if first != second:
        print("Passwords did not match; nothing changed.", file=sys.stderr)
        return 1
    if len(first) < 12:
        print("Use at least 12 characters; nothing changed.", file=sys.stderr)
        return 1

    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        first.encode("utf-8"),
        salt=salt,
        n=2**14,
        r=8,
        p=1,
        dklen=32,
    )
    session_secret = secrets.token_bytes(32)
    first = ""
    second = ""

    OUTPUT.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = OUTPUT.with_suffix(".env.tmp")
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
        0o600,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(f"CHAT_CAPTAIN_PASSWORD_SALT={salt.hex()}\n")
        handle.write(f"CHAT_CAPTAIN_PASSWORD_HASH={digest.hex()}\n")
        handle.write(f"CHAT_CAPTAIN_SESSION_SECRET={session_secret.hex()}\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, OUTPUT)
    os.chmod(OUTPUT, 0o600)
    print(f"Chat Captain credentials stored securely at {OUTPUT}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
