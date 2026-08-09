#!/usr/bin/env python3
"""Cache-first rich character voice rendering core with usage accounting."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import sqlite3
import tempfile
import threading
import urllib.request
import urllib.error
import wave
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol


MODEL = "gemini-3.1-flash-tts-preview"
SAMPLE_RATE = 24_000
OUTPUT_USD_PER_SECOND = 0.0005  # $20/M audio tokens, 25 tokens/second.


@dataclass(frozen=True)
class CharacterSpec:
    character_id: str
    revision: str
    name: str
    role: str
    voice_name: str
    vocal_identity: str
    expressive_bounds: str = "Natural and restrained; never imitate an identifiable real person."
    provenance: str = "synthetic-character"


@dataclass(frozen=True)
class PerformancePlan:
    intent: str
    audience: str
    setting: str
    affect: str
    pace: str
    restraint: str
    revision: str = "performance.v0.1"


@dataclass(frozen=True)
class RenderRequest:
    transcript: str
    character: CharacterSpec
    performance: PerformancePlan
    model: str = MODEL
    format: str = "wav-pcm16-24khz-mono"


class Provider(Protocol):
    def render_pcm(self, *, prompt: str, voice_name: str, model: str) -> bytes: ...


class BudgetExceeded(RuntimeError):
    pass


def compile_prompt(request: RenderRequest) -> str:
    character = request.character
    performance = request.performance
    return "\n".join(
        [
            f"# AUDIO PROFILE: {character.name}",
            f"Role: {character.role}. {character.vocal_identity}",
            f"Boundary: {character.expressive_bounds}",
            "# SCENE",
            f"{performance.setting}; addressing {performance.audience} with the intent to {performance.intent}.",
            "# DIRECTOR'S NOTES",
            f"Affect: {performance.affect}",
            f"Pace: {performance.pace}",
            f"Restraint: {performance.restraint}",
            "Keep the character recognizably continuous. Avoid melodrama. Recite the transcript exactly; do not add words.",
            "# TRANSCRIPT",
            request.transcript.strip(),
        ]
    )


def cache_key(request: RenderRequest) -> str:
    payload = json.dumps(asdict(request), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def estimate(request: RenderRequest) -> dict:
    # Deliberately conservative English estimate: about 12 spoken chars/sec.
    seconds = max(1.0, len(request.transcript.strip()) / 12.0)
    return {"seconds": seconds, "max_usd": seconds * OUTPUT_USD_PER_SECOND, "cache_key": cache_key(request)}


class GeminiTTSProvider:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Gemini API key is required")
        self.api_key = api_key

    def render_pcm(self, *, prompt: str, voice_name: str, model: str) -> bytes:
        """Call Gemini TTS.

        Repointed 2026-08-05. The original posted to `v1beta/interactions`
        with `response_format: {type: audio}` and read `output_audio.data` —
        a surface that no longer exists, so every render returned "response
        contained no output audio". It had never worked in production, and
        nothing noticed because the route to this service was also missing:
        the studio's 404 hid the fact that the pump was broken too.

        Current shape, verified against ai.google.dev rather than recalled:
        `models/{model}:generateContent`, `responseModalities: ["AUDIO"]`,
        and the audio arrives base64 at
        `candidates[0].content.parts[0].inlineData.data` as raw PCM,
        16-bit, 24 kHz, mono — which is exactly what `format` already
        promised.
        """
        body = json.dumps(
            {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "responseModalities": ["AUDIO"],
                    "speechConfig": {
                        "voiceConfig": {
                            "prebuiltVoiceConfig": {"voiceName": voice_name}
                        }
                    },
                },
            }
        ).encode()
        request = urllib.request.Request(
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent",
            data=body,
            headers={"x-goog-api-key": self.api_key,
                     "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                result = json.load(response)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:500]
            raise RuntimeError(f"Gemini TTS HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Gemini TTS unavailable: {exc.reason}") from exc

        try:
            part = result["candidates"][0]["content"]["parts"][0]
        except (KeyError, IndexError, TypeError):
            raise RuntimeError(
                "Gemini TTS returned no candidate part: "
                f"{json.dumps(result)[:300]}")
        inline = part.get("inlineData") or part.get("inline_data") or {}
        data = inline.get("data")
        if not data:
            raise RuntimeError(
                "Gemini TTS candidate carried no inline audio: "
                f"{json.dumps(part)[:300]}")
        return base64.b64decode(data)


class RichVoiceEngine:
    def __init__(self, root: Path, provider: Provider, **_legacy_limits):
        self.root = Path(root)
        self.audio_root = self.root / "audio"
        self.audio_root.mkdir(parents=True, exist_ok=True)
        self.provider = provider
        self._db_lock = threading.RLock()
        self._render_lock = threading.Lock()
        self.db = sqlite3.connect(self.root / "voice.sqlite3", check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS artifacts (
              cache_key TEXT PRIMARY KEY, path TEXT NOT NULL, request_json TEXT NOT NULL,
              seconds REAL NOT NULL, usd REAL NOT NULL, model TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS spend (
              id INTEGER PRIMARY KEY AUTOINCREMENT, day TEXT NOT NULL, cache_key TEXT NOT NULL UNIQUE,
              seconds REAL NOT NULL, usd REAL NOT NULL, state TEXT NOT NULL, created_at TEXT NOT NULL
            );
            """
        )
        # A reserved row belongs to an in-flight call in this process. On a
        # fresh engine there can be no surviving owner, so every reservation
        # found at startup is an interrupted render, not usage. Preserve the
        # evidence as failed instead of reporting it forever as active spend.
        with self.db:
            self.db.execute("UPDATE spend SET state='failed' WHERE state='reserved'")

    def _artifact(self, key: str):
        with self._db_lock:
            row = self.db.execute("SELECT * FROM artifacts WHERE cache_key = ?", (key,)).fetchone()
        return dict(row) if row and Path(row["path"]).exists() else None

    def render(self, request: RenderRequest) -> dict:
        # Provider calls remain serialized to prevent duplicate renders and
        # cache/accounting races. Database access uses its own short-held lock,
        # so /status and /budget stay live during a long Gemini request.
        with self._render_lock:
            return self._render_serial(request)

    def _render_serial(self, request: RenderRequest) -> dict:
        quote = estimate(request)
        key = quote["cache_key"]
        hit = self._artifact(key)
        if hit:
            return {**hit, "cache_hit": True}

        now = datetime.now(timezone.utc)
        day = now.date().isoformat()
        with self._db_lock, self.db:
            # A failed render leaves its row behind. Without this, the same
            # text can never be retried: the reservation collides on
            # cache_key and the request dies with an IntegrityError instead
            # of a budget message. Found 2026-08-05 when a provider fix made
            # the retry possible and the retry was refused by the ledger.
            self.db.execute(
                "DELETE FROM spend WHERE cache_key=? AND state='failed'", (key,))
            self.db.execute(
                "INSERT INTO spend(day,cache_key,seconds,usd,state,created_at) VALUES(?,?,?,?,?,?)",
                (day, key, quote["seconds"], quote["max_usd"], "reserved", now.isoformat()),
            )

        try:
            pcm = self.provider.render_pcm(prompt=compile_prompt(request), voice_name=request.character.voice_name, model=request.model)
            seconds = len(pcm) / (SAMPLE_RATE * 2)
            usd = seconds * OUTPUT_USD_PER_SECOND
            path = self.audio_root / f"{key}.wav"
            with tempfile.NamedTemporaryFile(dir=self.audio_root, suffix=".wav", delete=False) as temp:
                temp_path = Path(temp.name)
            try:
                with wave.open(str(temp_path), "wb") as output:
                    output.setnchannels(1)
                    output.setsampwidth(2)
                    output.setframerate(SAMPLE_RATE)
                    output.writeframes(pcm)
                os.replace(temp_path, path)
            finally:
                temp_path.unlink(missing_ok=True)
            artifact = {
                "cache_key": key, "path": str(path), "request_json": json.dumps(asdict(request), sort_keys=True),
                "seconds": seconds, "usd": usd, "model": request.model, "created_at": now.isoformat(),
            }
            with self._db_lock, self.db:
                self.db.execute(
                    "INSERT INTO artifacts(cache_key,path,request_json,seconds,usd,model,created_at) VALUES(:cache_key,:path,:request_json,:seconds,:usd,:model,:created_at)", artifact
                )
                self.db.execute("UPDATE spend SET seconds=?, usd=?, state='complete' WHERE cache_key=?", (seconds, usd, key))
            return {**artifact, "cache_hit": False}
        except Exception:
            with self._db_lock, self.db:
                self.db.execute("UPDATE spend SET state='failed' WHERE cache_key=?", (key,))
            raise

    def budget(self) -> dict:
        day = datetime.now(timezone.utc).date().isoformat()
        with self._db_lock:
            used = self.db.execute(
                "SELECT COALESCE(SUM(seconds),0) seconds, COALESCE(SUM(usd),0) usd FROM spend WHERE day=? AND state IN ('reserved','complete')", (day,)
            ).fetchone()
        return {
            "day": day, "seconds_used": used["seconds"], "seconds_limit": None,
            "usd_used": used["usd"], "usd_limit": None, "enforced": False,
        }
