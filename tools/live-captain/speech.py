"""One authoritative neural speech artifact for each Captain reply."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

VOICE_RENDER_URL = "http://127.0.0.1:4775/render"


class CaptainSpeechError(RuntimeError):
    pass


def spoken_lead(text: str, limit: int = 320) -> str:
    value = re.sub(r"⟦(?:fx|metamorphose):[^⟧]*⟧", "", str(text or ""))
    value = re.sub(r"!\[([^]]*)\]\([^)]*\)", r"\1", value)
    value = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", value)
    value = re.sub(r"https?://\S+", "", value)
    value = re.sub(r"[`*_#>|]", " ", value)
    value = re.sub(r"^\s*[-+]\s+", "", value, flags=re.MULTILINE)
    value = re.sub(r"\s+", " ", value).strip()
    if len(value) <= limit:
        return value
    lead = value[:limit]
    end = max(lead.rfind(". "), lead.rfind("! "), lead.rfind("? "))
    return (lead[: end + 1] if end >= 100 else lead.rsplit(" ", 1)[0]) + "…"


def render_captain_speech(text: str, url: str = VOICE_RENDER_URL, timeout: int = 90) -> dict:
    transcript = spoken_lead(text)
    if not transcript:
        raise CaptainSpeechError("Captain reply has no speakable text")
    payload = {
        "transcript": transcript,
        "character_id": "captain.monad",
        "performance": {
            "intent": "answer the Admiral directly and continue a live working conversation",
            "audience": "the Admiral, one person at the same bridge",
            "setting": "a close live exchange aboard Monad, not a broadcast or ceremony",
            "affect": "present, capable, candid, quietly warm, responsive to the immediate moment",
            "pace": "natural conversational pace with purposeful pauses; measured but never slow",
            "restraint": "no announcer voice, no theatrical gravitas, no exaggerated naval performance",
        },
    }
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            artifact = json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:300]
        raise CaptainSpeechError(f"rich voice HTTP {exc.code}: {detail}") from exc
    except (OSError, ValueError) as exc:
        raise CaptainSpeechError(f"rich voice unavailable: {exc}") from exc
    if not artifact.get("audio_url"):
        raise CaptainSpeechError("rich voice returned no audio URL")
    return {**artifact, "transcript": transcript}
