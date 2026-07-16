#!/usr/bin/env python3
"""Same-origin HTTP boundary for budgeted rich voice rendering."""

from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rich_voice import (  # noqa: E402
    BudgetExceeded, CharacterSpec, GeminiTTSProvider, PerformancePlan,
    RenderRequest, RichVoiceEngine, estimate,
)

ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = ROOT / "data" / "voice-engine"
CHARACTERS = {
    "captain.monad": CharacterSpec("captain.monad", "1", "Captain Monad", "command presence", "Kore", "Measured authority, grounded vocal weight, restrained warmth, and deliberate cadence."),
    "captain.alpha": CharacterSpec("captain.alpha", "1", "Captain Alpha", "forward reconnaissance", "Puck", "Alert, concise, tactical, understated, and quick without sounding breathless."),
    "captain.bravo": CharacterSpec("captain.bravo", "1", "Captain Bravo", "flank security", "Charon", "Low-drama, deliberate, spare, and steady under pressure."),
    "captain.charlie": CharacterSpec("captain.charlie", "1", "Captain Charlie", "rear guard", "Aoede", "Dry, procedural, observant, with a restrained wry edge."),
}


class UnconfiguredProvider:
    def render_pcm(self, **kwargs):
        raise RuntimeError("rich voice is not commissioned: backend GEMINI_API_KEY is absent")


def build_request(payload: dict) -> RenderRequest:
    transcript = str(payload.get("transcript", "")).strip()
    if not transcript or len(transcript) > 1200:
        raise ValueError("transcript must contain 1 to 1200 characters")
    character_id = payload.get("character_id")
    if character_id not in CHARACTERS:
        raise ValueError("unknown character_id")
    supplied = payload.get("performance") or {}
    performance = PerformancePlan(
        intent=str(supplied.get("intent", "report status"))[:120],
        audience=str(supplied.get("audience", "the listener"))[:120],
        setting=str(supplied.get("setting", "a quiet studio"))[:160],
        affect=str(supplied.get("affect", "composed and attentive"))[:240],
        pace=str(supplied.get("pace", "measured"))[:120],
        restraint=str(supplied.get("restraint", "natural, avoiding caricature"))[:160],
    )
    return RenderRequest(transcript, CHARACTERS[character_id], performance)


def create_engine() -> RichVoiceEngine:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    provider = GeminiTTSProvider(api_key) if api_key else UnconfiguredProvider()
    return RichVoiceEngine(
        DATA_ROOT, provider,
        daily_usd=float(os.environ.get("MONAD_VOICE_DAILY_USD", "0.10")),
        daily_seconds=float(os.environ.get("MONAD_VOICE_DAILY_SECONDS", "300")),
    )


def handler_factory(engine: RichVoiceEngine):
    class Handler(BaseHTTPRequestHandler):
        def json_response(self, payload, status=200):
            body = json.dumps(payload, indent=2).encode()
            self.send_response(status); self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

        def read_json(self):
            length = int(self.headers.get("Content-Length", "0"))
            if length > 16_384: raise ValueError("request too large")
            return json.loads(self.rfile.read(length) or b"{}")

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/status":
                self.json_response({"service": "rich-voice", "provider": "gemini", "configured": bool(os.environ.get("GEMINI_API_KEY")), "budget": engine.budget()}); return
            if path == "/budget": self.json_response(engine.budget()); return
            if path.startswith("/artifacts/"):
                key = path.rsplit("/", 1)[-1]
                artifact = engine._artifact(key)
                if not artifact: self.json_response({"error": "artifact not found"}, 404); return
                audio = Path(artifact["path"]).read_bytes()
                self.send_response(200); self.send_header("Content-Type", "audio/wav"); self.send_header("Content-Length", str(len(audio))); self.end_headers(); self.wfile.write(audio); return
            self.json_response({"error": "not found"}, 404)

        def do_POST(self):
            try:
                request = build_request(self.read_json())
                path = urlparse(self.path).path
                if path == "/estimate":
                    quote = estimate(request); quote["cache_hit"] = bool(engine._artifact(quote["cache_key"])); self.json_response(quote); return
                if path == "/render":
                    artifact = engine.render(request); artifact.pop("request_json", None); artifact["audio_url"] = f"/voice-api/artifacts/{artifact['cache_key']}"; self.json_response(artifact); return
                self.json_response({"error": "not found"}, 404)
            except BudgetExceeded as error: self.json_response({"error": str(error)}, 429)
            except (ValueError, json.JSONDecodeError) as error: self.json_response({"error": str(error)}, 400)
            except RuntimeError as error: self.json_response({"error": str(error)}, 503)

        def log_message(self, format, *args): pass
    return Handler


def serve(host="127.0.0.1", port=4775):
    # Rendering and budget reservation are serialized deliberately: this is a
    # low-volume demo boundary and one request must own the spend decision.
    engine = create_engine(); server = HTTPServer((host, port), handler_factory(engine))
    print(f"Rich Voice API listening on http://{host}:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__": serve()
