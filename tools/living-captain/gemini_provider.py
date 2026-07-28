"""Gemini inference adapter. It owns no Captain identity or state."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from model_provider import GenerationLimits, Message, ProviderError, ProviderResponse


API_ORIGIN = "https://generativelanguage.googleapis.com"
API_VERSION = "v1beta"
DEFAULT_MODEL = "gemini-3.5-flash-lite"


class GeminiProvider:
    name = "Gemini"

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        api_key = api_key.strip()
        if not api_key:
            raise ValueError("Gemini API key is missing")
        self._api_key = api_key
        self.model = model

    def generate(
        self,
        system_prompt: str,
        messages: list[Message],
        limits: GenerationLimits,
    ) -> ProviderResponse:
        url = f"{API_ORIGIN}/{API_VERSION}/models/{self.model}:generateContent"
        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [
                {
                    "role": "model" if message.role == "assistant" else "user",
                    "parts": [{"text": message.content}],
                }
                for message in messages
            ],
            "generationConfig": {
                "maxOutputTokens": limits.max_output_tokens,
                "thinkingConfig": {"thinkingLevel": "minimal"},
            },
        }
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self._api_key,
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                result = json.load(response)
        except urllib.error.HTTPError as error:
            message = _safe_http_error(error).replace(self._api_key, "[REDACTED]")
            raise ProviderError(f"Gemini returned HTTP {error.code}: {message}") from None
        except (urllib.error.URLError, TimeoutError) as error:
            raise ProviderError(f"Gemini is unavailable: {type(error).__name__}") from None
        except (json.JSONDecodeError, OSError, ValueError):
            raise ProviderError("Gemini returned an unreadable response") from None

        candidates = result.get("candidates") or []
        if not candidates:
            raise ProviderError("Gemini returned no reply")
        candidate = candidates[0]
        parts = candidate.get("content", {}).get("parts", [])
        text = "".join(str(part.get("text", "")) for part in parts).strip()
        if not text:
            raise ProviderError("Gemini returned an empty reply")

        usage = result.get("usageMetadata", {})
        return ProviderResponse(
            text=text,
            provider=self.name,
            model=result.get("modelVersion", self.model),
            input_tokens=_optional_int(usage.get("promptTokenCount")),
            output_tokens=_optional_int(usage.get("candidatesTokenCount")),
            total_tokens=_optional_int(usage.get("totalTokenCount")),
            finish_reason=candidate.get("finishReason"),
        )


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) and value >= 0 else None


def _safe_http_error(error: urllib.error.HTTPError) -> str:
    try:
        body = error.read(16_384).decode("utf-8", errors="replace")
        detail = json.loads(body).get("error", {})
        message = str(detail.get("message", "request rejected"))
    except (OSError, ValueError, AttributeError):
        message = "request rejected"
    # Provider errors should be concise and must never echo credentials.
    return message[:500]
