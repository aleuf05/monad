"""Card Generation Engine for Monad CardMaker v0.1.

Decoupled generation architecture:
- CardGenerator (abstract base / protocol)
- LLMCardGenerator (Gemini/OpenAI API fallback)
- DeterministicCardGenerator (Rich, rule-based fallback working offline)
"""

from __future__ import annotations

import json
import os
import random
import urllib.request
import urllib.error
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any


@dataclass
class CardInput:
    recipient: str
    occasion: str
    relationship: str
    details: str
    tone: str  # Warm, Funny, Sentimental, Weird, Surprise Me


@dataclass
class CardTheme:
    color_primary: str
    color_secondary: str
    color_bg: str
    color_text: str
    font_family: str
    svg_icon: str
    pattern_style: str


@dataclass
class CardContent:
    front_headline: str
    front_subtitle: str
    inside_quote: str
    inside_message: str
    closing_signature: str
    theme: CardTheme

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Pre-defined theme palettes matched to interests / tones / occasions
THEMES = {
    "aviation": CardTheme(
        color_primary="#0f4c81",
        color_secondary="#e5a93b",
        color_bg="#f4f8fb",
        color_text="#1c2d42",
        font_family="'Inter', sans-serif",
        svg_icon="plane",
        pattern_style="sky-cloud"
    ),
    "nature": CardTheme(
        color_primary="#2d6a4f",
        color_secondary="#d8f3dc",
        color_bg="#f7fbf7",
        color_text="#1b4332",
        font_family="'Georgia', serif",
        svg_icon="leaf",
        pattern_style="botanical"
    ),
    "space": CardTheme(
        color_primary="#2b1e66",
        color_secondary="#f72585",
        color_bg="#0b091a",
        color_text="#e0aaff",
        font_family="'Inter', sans-serif",
        svg_icon="star",
        pattern_style="constellation"
    ),
    "funny": CardTheme(
        color_primary="#ff595e",
        color_secondary="#ffca3a",
        color_bg="#fffdf7",
        color_text="#2b2d42",
        font_family="'Caveat', cursive, sans-serif",
        svg_icon="sparkles",
        pattern_style="confetti"
    ),
    "warm": CardTheme(
        color_primary="#b5838d",
        color_secondary="#e56b6f",
        color_bg="#fff9f5",
        color_text="#4a4e69",
        font_family="'Playfair Display', serif",
        svg_icon="heart",
        pattern_style="warm-dots"
    ),
    "weird": CardTheme(
        color_primary="#7209b7",
        color_secondary="#4cc9f0",
        color_bg="#f8f7ff",
        color_text="#3a0ca3",
        font_family="'Space Mono', monospace",
        svg_icon="alien",
        pattern_style="geo-grid"
    ),
    "default": CardTheme(
        color_primary="#3a5a40",
        color_secondary="#a3b18a",
        color_bg="#fefae0",
        color_text="#343a40",
        font_family="'Inter', sans-serif",
        svg_icon="crown",
        pattern_style="minimal"
    )
}


SVG_ICONS = {
    "plane": '<path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z" fill="currentColor"/>',
    "leaf": '<path d="M17 8C8 10 59 16.17 3.83 12l1.42-1.42c3.84 3.84 9.68 4.25 14.07 1.07l-3.32-3.32c-.39-.39-.39-1.02 0-1.41.39-.39 1.02-.39 1.41 0l3.32 3.32c3.18-4.39 2.77-10.23-1.07-14.07z" fill="currentColor"/>',
    "star": '<path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z" fill="currentColor"/>',
    "sparkles": '<path d="M12 3l2.2 4.8L19 10l-4.8 2.2L12 17l-2.2-4.8L5 10l4.8-2.2zM5 3l1.1 2.4L8.5 6.5 6.1 7.6 5 10 3.9 7.6 1.5 6.5l2.4-1.1z" fill="currentColor"/>',
    "heart": '<path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" fill="currentColor"/>',
    "alien": '<path d="M12 2C6.48 2 2 6.48 2 12c0 3.69 2.47 6.86 6 8.25V22h8v-1.75c3.53-1.39 6-4.56 6-8.25 0-5.52-4.48-10-10-10zm-3 10c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm6 0c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2z" fill="currentColor"/>',
    "crown": '<path d="M5 16L3 5l5.5 5L12 4l3.5 6L21 5l-2 11H5zm14 3c0 .55-.45 1-1 1H6c-.55 0-1-.45-1-1v-1h14v1z" fill="currentColor"/>'
}


class DeterministicCardGenerator:
    """Rich rule-based card generator. Guaranteed fast & deterministic offline."""

    def generate(self, card_input: CardInput) -> CardContent:
        tone = (card_input.tone or "Warm").strip().title()
        if tone == "Surprise Me":
            tone = random.choice(["Warm", "Funny", "Sentimental", "Weird"])

        recipient = card_input.recipient.strip() or "Friend"
        occasion = card_input.occasion.strip() or "Special Day"
        relationship = card_input.relationship.strip() or "Loved One"
        details = card_input.details.strip()

        # Select theme based on details or tone
        details_lower = details.lower()
        if any(w in details_lower for w in ["pilot", "plane", "aviation", "flight", "sky", "fly"]):
            theme_key = "aviation"
        elif any(w in details_lower for w in ["garden", "nature", "forest", "hiking", "flower"]):
            theme_key = "nature"
        elif any(w in details_lower for w in ["star", "space", "astronomy", "galaxy", "sci-fi"]):
            theme_key = "space"
        elif tone.lower() == "funny":
            theme_key = "funny"
        elif tone.lower() == "sentimental":
            theme_key = "warm"
        elif tone.lower() == "weird":
            theme_key = "weird"
        else:
            theme_key = "warm"

        base_theme = THEMES.get(theme_key, THEMES["default"])

        # Craft Headline & Subtitle
        headline, subtitle = self._generate_headline(recipient, occasion, details, tone)

        # Craft Quote & Main Message
        inside_quote, inside_message = self._generate_message(recipient, occasion, relationship, details, tone)

        # Craft Closing / Signature
        signature = self._generate_signature(relationship, tone)

        return CardContent(
            front_headline=headline,
            front_subtitle=subtitle,
            inside_quote=inside_quote,
            inside_message=inside_message,
            closing_signature=signature,
            theme=base_theme
        )

    def _generate_headline(self, recipient: str, occasion: str, details: str, tone: str) -> tuple[str, str]:
        details_short = details.split(',')[0].strip() if details else ""
        
        if tone == "Funny":
            headlines = [
                f"To {recipient}: Proof That You're Still Our Favorite!",
                f"Happy {occasion}, {recipient}!",
                f"Look Who's Celebrating: The One and Only {recipient}!",
                f"Notice: {recipient} is Officially Awesome Today."
            ]
            subtitles = [
                f"Yes, even with the whole '{details_short}' obsession." if details_short else "Handle with care and lots of cake.",
                "Another year wiser, or at least better at pretending!",
                f"Specially commissioned for our favorite {recipient}."
            ]
        elif tone == "Weird":
            headlines = [
                f"Greetings, Earthling {recipient}!",
                f"{recipient}: Cosmic Anomalies Celebrate You!",
                f"Happy {occasion} Across All Parallel Timelines!"
            ]
            subtitles = [
                f"The radar indicates high levels of {details_short} ahead." if details_short else "Gravity is optional today.",
                "Transmitted via sub-space telemetry with maximum enthusiasm."
            ]
        elif tone == "Sentimental":
            headlines = [
                f"For {recipient}, With Endless Gratitude",
                f"Celebrating You, Dearest {recipient}",
                f"To {recipient}: On This Beautiful {occasion}"
            ]
            subtitles = [
                f"Thank you for bringing your passion for {details_short} into our lives." if details_short else "A small token of boundless appreciation.",
                "Some people make the world brighter just by being in it."
            ]
        else:  # Warm / default
            headlines = [
                f"Happy {occasion}, {recipient}!",
                f"To the Wonderful {recipient}",
                f"Cheers to You, {recipient}!"
            ]
            subtitles = [
                f"Here's to high flights and great adventures in {details_short}!" if "aviation" in details_short.lower() or "plane" in details_short.lower() else (f"Celebrating your love for {details_short}!" if details_short else "Wishing you a joy-filled day."),
                "May your day be filled with warm smiles and favorite things."
            ]

        return random.choice(headlines), random.choice(subtitles)

    def _generate_message(self, recipient: str, occasion: str, relationship: str, details: str, tone: str) -> tuple[str, str]:
        has_aviation = any(w in details.lower() for w in ["aviation", "plane", "fly", "flight", "pilot"])

        if tone == "Funny":
            quote = "“Age is merely the number of years the world has been enjoying us.”"
            if has_aviation:
                msg = (
                    f"Dear {recipient},\n\n"
                    f"Happy {occasion}! We know you'd probably rather be up in the clouds or building your latest "
                    f"aircraft, but we insisted on grounding you long enough to celebrate! "
                    f"May your day have smooth skies, clear runways, and zero turbulence. "
                    f"Keep soaring high (and maybe leave some altitude for the rest of us)!"
                )
            elif details:
                msg = (
                    f"Dear {recipient},\n\n"
                    f"Happy {occasion}! On your special day, we wanted to honor the legendary {recipient}—"
                    f"especially your unmatched passion for {details}. "
                    f"Never change, keep being uniquely you, and enjoy every single minute of your celebration!"
                )
            else:
                msg = (
                    f"Dear {recipient},\n\n"
                    f"Happy {occasion}! Wishing you a fantastic day filled with laughter, great food, "
                    f"and zero adult responsibilities."
                )
        elif tone == "Sentimental":
            quote = "“The best things in life are the people we love and the memories we make.”"
            if has_aviation:
                msg = (
                    f"Dearest {recipient},\n\n"
                    f"On this {occasion}, I want to take a moment to express how much you mean to us as a {relationship.lower()}. "
                    f"Just like your love for aviation, you inspire everyone around you to reach new heights. "
                    f"Thank you for your warmth, wisdom, and steady presence. Wishing you blue skies always."
                )
            elif details:
                msg = (
                    f"Dearest {recipient},\n\n"
                    f"Wishing you a deeply meaningful {occasion}. Having you as a {relationship.lower()} is a true gift. "
                    f"Seeing the joy and dedication you bring to {details} reminds us to cherish the things that matter most. "
                    f"May this year bring you as much happiness as you give to everyone around you."
                )
            else:
                msg = (
                    f"Dearest {recipient},\n\n"
                    f"Wishing you a wonderful {occasion}. Thank you for being such a constant source of kindness and joy. "
                    f"You are truly appreciated today and every day."
                )
        elif tone == "Weird":
            quote = "“Normal is just a setting on the washing machine.”"
            msg = (
                f"Greetings {recipient},\n\n"
                f"The galactic committee has assembled on this {occasion} to certify that you are 100% extraordinary. "
                f"Our sensors detect intense energy surrounding {details or 'your existence'}. "
                f"Continue operating at maximum power!"
            )
        else:  # Warm
            quote = "“May your heart be light, your days be bright, and your year be full of delight.”"
            if has_aviation:
                msg = (
                    f"Dear {recipient},\n\n"
                    f"Wishing you a very Happy {occasion}! Whether you're navigating the skies or enjoying time with family, "
                    f"you bring so much passion and energy into everything you do. "
                    f"Here's to smooth flying, new horizons, and a fantastic year ahead!"
                )
            elif details:
                msg = (
                    f"Dear {recipient},\n\n"
                    f"Happy {occasion}! It's a joy celebrating someone as wonderful as you. "
                    f"From your enthusiasm for {details} to the great times we share, you make every day brighter. "
                    f"Have an incredible day!"
                )
            else:
                msg = (
                    f"Dear {recipient},\n\n"
                    f"Happy {occasion}! Sending you the warmest wishes for a day filled with happiness, relaxation, "
                    f"and everything you love."
                )

        return quote, msg

    def _generate_signature(self, relationship: str, tone: str) -> str:
        if tone == "Funny":
            closings = ["With high regard & extra cake,", "Your favorite fans,", "Cheering you on,"]
        elif tone == "Sentimental":
            closings = ["With all our love,", "Forever grateful,", "Warmest blessings,"]
        elif tone == "Weird":
            closings = ["Over and out,", "Transmission ends,", "In cosmic solidarity,"]
        else:
            closings = ["With love & best wishes,", "Warmly,", "Cheers,"]

        closing = random.choice(closings)
        rel_str = f"Your {relationship}" if relationship and relationship.lower() != "friend" else "Your Family & Friends"
        return f"{closing}\n{rel_str}"


class LLMCardGenerator:
    """LLM-backed card generator using Gemini / HTTP API if configured, falling back smoothly."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY")
        self.fallback = DeterministicCardGenerator()

    def generate(self, card_input: CardInput) -> CardContent:
        if not self.api_key:
            return self.fallback.generate(card_input)

        try:
            # Simple HTTP JSON call to Gemini API if key is set
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
            prompt = (
                f"You are a master greeting card creator. Generate a highly personalized greeting card.\n"
                f"Recipient: {card_input.recipient}\n"
                f"Occasion: {card_input.occasion}\n"
                f"Relationship: {card_input.relationship}\n"
                f"Personal details: {card_input.details}\n"
                f"Tone: {card_input.tone}\n\n"
                f"Return ONLY a JSON object with keys: front_headline, front_subtitle, inside_quote, inside_message, closing_signature."
            )
            req_data = json.dumps({
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"response_mime_type": "application/json"}
            }).encode('utf-8')

            req = urllib.request.Request(url, data=req_data, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                text_out = result['candidates'][0]['content']['parts'][0]['text']
                data = json.loads(text_out)

                base_card = self.fallback.generate(card_input)
                return CardContent(
                    front_headline=data.get('front_headline', base_card.front_headline),
                    front_subtitle=data.get('front_subtitle', base_card.front_subtitle),
                    inside_quote=data.get('inside_quote', base_card.inside_quote),
                    inside_message=data.get('inside_message', base_card.inside_message),
                    closing_signature=data.get('closing_signature', base_card.closing_signature),
                    theme=base_card.theme
                )
        except Exception:
            # On any network failure / timeout / API issue, fall back seamlessly
            return self.fallback.generate(card_input)


class CardGeneratorEngine:
    """Unified entry point for Card Generation."""

    def __init__(self):
        self.llm_generator = LLMCardGenerator()
        self.fallback_generator = DeterministicCardGenerator()

    def create_card(self, card_input: CardInput) -> CardContent:
        if self.llm_generator.api_key:
            return self.llm_generator.generate(card_input)
        return self.fallback_generator.generate(card_input)
