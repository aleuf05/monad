#!/usr/bin/env python3
"""Cache-first, budget-bounded rich character voice rendering core."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import sqlite3
import tempfile
import urllib.request
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
        body = json.dumps(
            {
                "model": model,
                "input": prompt,
                "response_format": {"type": "audio"},
                "generation_config": {"speech_config": [{"voice": voice_name}]},
            }
        ).encode()
        request = urllib.request.Request(
            "https://generativelanguage.googleapis.com/v1beta/interactions",
            data=body,
            headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=90) as response:
            result = json.load(response)
        audio = result.get("output_audio") or result.get("outputAudio") or {}
        data = audio.get("data")
        if not data:
            raise RuntimeError("Gemini TTS response contained no output audio")
        return base64.b64decode(data)


class RichVoiceEngine:
    def __init__(self, root: Path, provider: Provider, *, daily_usd: float = 0.10, daily_seconds: float = 300):
        self.root = Path(root)
        self.audio_root = self.root / "audio"
        self.audio_root.mkdir(parents=True, exist_ok=True)
        self.provider = provider
        self.daily_usd = daily_usd
        self.daily_seconds = daily_seconds
        self.db = sqlite3.connect(self.root / "voice.sqlite3")
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

    def _artifact(self, key: str):
        row = self.db.execute("SELECT * FROM artifacts WHERE cache_key = ?", (key,)).fetchone()
        return dict(row) if row and Path(row["path"]).exists() else None

    def render(self, request: RenderRequest) -> dict:
        quote = estimate(request)
        key = quote["cache_key"]
        hit = self._artifact(key)
        if hit:
            return {**hit, "cache_hit": True}

        now = datetime.now(timezone.utc)
        day = now.date().isoformat()
        with self.db:
            used = self.db.execute(
                "SELECT COALESCE(SUM(seconds),0) seconds, COALESCE(SUM(usd),0) usd FROM spend WHERE day=? AND state IN ('reserved','complete')",
                (day,),
            ).fetchone()
            if used["seconds"] + quote["seconds"] > self.daily_seconds or used["usd"] + quote["max_usd"] > self.daily_usd:
                raise BudgetExceeded("daily rich-voice budget exhausted")
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
            with self.db:
                self.db.execute(
                    "INSERT INTO artifacts(cache_key,path,request_json,seconds,usd,model,created_at) VALUES(:cache_key,:path,:request_json,:seconds,:usd,:model,:created_at)", artifact
                )
                self.db.execute("UPDATE spend SET seconds=?, usd=?, state='complete' WHERE cache_key=?", (seconds, usd, key))
            return {**artifact, "cache_hit": False}
        except Exception:
            with self.db:
                self.db.execute("UPDATE spend SET state='failed' WHERE cache_key=?", (key,))
            raise

    def budget(self) -> dict:
        day = datetime.now(timezone.utc).date().isoformat()
        used = self.db.execute(
            "SELECT COALESCE(SUM(seconds),0) seconds, COALESCE(SUM(usd),0) usd FROM spend WHERE day=? AND state IN ('reserved','complete')", (day,)
        ).fetchone()
        return {
            "day": day, "seconds_used": used["seconds"], "seconds_limit": self.daily_seconds,
            "usd_used": used["usd"], "usd_limit": self.daily_usd,
        }
