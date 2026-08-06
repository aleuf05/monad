"""Password + signed-session auth for Root Console.

Adapted directly from tools/living-captain/web_service.py's AuthConfig
(scrypt password hash, HMAC-signed session token) -- same proven pattern,
extracted into its own module. NOTE: the session cookie here omits the
`Secure` attribute, unlike living-captain's, because this service is
currently served over plain HTTP on loopback (no TLS yet). Add `Secure`
back the moment this sits behind Caddy/TLS for LAN access -- do not expose
this to LAN over plain HTTP with a cookie that could be intercepted.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import time

COOKIE_NAME = "root_console_session"
SESSION_SECONDS = 12 * 60 * 60
LOGIN_WINDOW_SECONDS = 60
LOGIN_ATTEMPTS_PER_WINDOW = 5


class AuthConfig:
    def __init__(self, salt: bytes, password_hash: bytes, session_secret: bytes):
        self.salt = salt
        self.password_hash = password_hash
        self.session_secret = session_secret

    @classmethod
    def from_environment(cls) -> "AuthConfig":
        try:
            return cls(
                bytes.fromhex(os.environ["ROOT_CONSOLE_PASSWORD_SALT"]),
                bytes.fromhex(os.environ["ROOT_CONSOLE_PASSWORD_HASH"]),
                bytes.fromhex(os.environ["ROOT_CONSOLE_SESSION_SECRET"]),
            )
        except (KeyError, ValueError) as error:
            raise ValueError("Root Console authentication is not configured") from error

    def verify_password(self, password: str) -> bool:
        candidate = hashlib.scrypt(
            password.encode("utf-8"), salt=self.salt, n=2**14, r=8, p=1, dklen=32
        )
        return hmac.compare_digest(candidate, self.password_hash)

    def issue_session(self, now: int | None = None) -> str:
        timestamp = int(time.time()) if now is None else now
        payload = f"{timestamp}.{secrets.token_hex(16)}"
        signature = hmac.new(self.session_secret, payload.encode("ascii"), hashlib.sha256).digest()
        encoded = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
        return f"{payload}.{encoded}"

    def verify_session(self, token: str, now: int | None = None) -> bool:
        try:
            timestamp_text, nonce, supplied = token.split(".", 2)
            timestamp = int(timestamp_text)
        except (ValueError, AttributeError):
            return False
        current = int(time.time()) if now is None else now
        if timestamp > current + 60 or current - timestamp > SESSION_SECONDS:
            return False
        payload = f"{timestamp}.{nonce}"
        signature = hmac.new(self.session_secret, payload.encode("ascii"), hashlib.sha256).digest()
        expected = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
        return hmac.compare_digest(expected, supplied)


class LoginLimiter:
    def __init__(self):
        import threading

        self._lock = threading.Lock()
        self._attempts: list[float] = []

    def allow(self) -> bool:
        now = time.monotonic()
        with self._lock:
            self._attempts = [a for a in self._attempts if now - a < LOGIN_WINDOW_SECONDS]
            if len(self._attempts) >= LOGIN_ATTEMPTS_PER_WINDOW:
                return False
            self._attempts.append(now)
            return True
