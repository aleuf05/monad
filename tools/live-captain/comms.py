"""Canonical Communication Model & Transport Abstraction for Live Captain.

Governing rule: Capability belongs to the message; presentation belongs to the channel.
Provides transport-neutral message structures, action schemas, authority boundaries,
and channel adapters.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
import enum
import json
import time
from typing import Any, Dict, List, Optional


class AuthorityLevel(str, enum.Enum):
    CONVERSATIONAL = "conversational"       # Safe read/dialogue, explanations
    PROPOSED = "proposed"                   # Mutation staged/prepared, awaiting confirmation
    AUTHORIZED = "authorized"               # Direct execution within non-privileged scope
    PRIVILEGED_STAGED = "privileged_staged" # Requires sudo, staged to cmd.sh only


class Urgency(str, enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    EMERGENCY = "emergency"


@dataclass
class MediaItem:
    media_type: str                         # "image", "document", "audio", "video", "code"
    url: str                                # Web-accessible URL
    local_path: Optional[str] = None        # Absolute filesystem path if local
    alt: str = ""
    mime_type: str = ""
    size_bytes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MediaItem:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Action:
    id: str
    label: str
    intent: str
    authority_level: str = AuthorityLevel.CONVERSATIONAL.value
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Action:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class InboundMessage:
    channel: str                            # "phone_web", "root_console", "telegram", "internal"
    sender: str                             # "admiral", "system", "agent"
    conversation_id: str
    text: str
    media: List[MediaItem] = field(default_factory=list)
    reply_to: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    channel_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = dataclasses.asdict(self)
        d["media"] = [m.to_dict() if isinstance(m, MediaItem) else m for m in self.media]
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> InboundMessage:
        media_list = [MediaItem.from_dict(m) if isinstance(m, dict) else m for m in data.get("media", [])]
        clean_data = {k: v for k, v in data.items() if k in cls.__dataclass_fields__ and k != "media"}
        return cls(media=media_list, **clean_data)


@dataclass
class OutboundMessage:
    destination: str                        # Channel or client ID
    text: str
    media: List[MediaItem] = field(default_factory=list)
    actions: List[Action] = field(default_factory=list)
    urgency: str = Urgency.NORMAL.value
    reply_to: Optional[str] = None
    semantic_role: str = "captain"          # "captain", "engineering", "alert"
    channel_hints: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        d = dataclasses.asdict(self)
        d["media"] = [m.to_dict() if isinstance(m, MediaItem) else m for m in self.media]
        d["actions"] = [a.to_dict() if isinstance(a, Action) else a for a in self.actions]
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> OutboundMessage:
        media_list = [MediaItem.from_dict(m) if isinstance(m, dict) else m for m in data.get("media", [])]
        action_list = [Action.from_dict(a) if isinstance(a, dict) else a for a in data.get("actions", [])]
        clean_data = {k: v for k, v in data.items() if k in cls.__dataclass_fields__ and k not in ("media", "actions")}
        return cls(media=media_list, actions=action_list, **clean_data)


class AuthorityBoundary:
    """Classifies Admiral intent and enforces operation safety gates."""

    PRIVILEGED_COMMANDS = {
        "systemctl restart", "systemctl stop", "systemctl start",
        "reboot", "shutdown", "rm -rf /", "mkfs", "iptables", "caddy reload"
    }

    @classmethod
    def assess(cls, text: str) -> AuthorityLevel:
        lower = text.strip().lower()

        # Questions or explanations
        if any(lower.startswith(q) for q in ["explain", "what is", "why", "how does", "what would", "describe"]):
            return AuthorityLevel.CONVERSATIONAL

        # Staging / Preparation
        if any(p in lower for p in ["prepare to", "draft", "propose", "plan", "dry-run", "preview"]):
            return AuthorityLevel.PROPOSED

        # Privileged system checks
        if any(cmd in lower for cmd in cls.PRIVILEGED_COMMANDS) or "sudo " in lower:
            return AuthorityLevel.PRIVILEGED_STAGED

        # Standard non-privileged execution
        return AuthorityLevel.AUTHORIZED


class ChannelAdapter:
    """Base interface for transport-specific presentation encoding/decoding."""

    channel_name: str = "base"

    def format_outbound(self, message: OutboundMessage) -> Any:
        raise NotImplementedError

    def parse_inbound(self, raw_payload: Any) -> InboundMessage:
        raise NotImplementedError


class WebChannelAdapter(ChannelAdapter):
    """Encodes OutboundMessage for Web Phone Terminal & Root Console SSE."""

    channel_name: str = "phone_web"

    def format_outbound(self, message: OutboundMessage) -> Dict[str, Any]:
        return {
            "type": "message",
            "role": message.semantic_role,
            "text": message.text,
            "media": [m.to_dict() for m in message.media],
            "actions": [a.to_dict() for a in message.actions],
            "urgency": message.urgency,
            "reply_to": message.reply_to,
            "ts": message.timestamp,
        }

    def parse_inbound(self, raw_payload: Dict[str, Any]) -> InboundMessage:
        attachments = raw_payload.get("attachments", [])
        media_items = []
        for att in attachments:
            url = att.get("url") or f"/data/live-captain/uploads/{att.get('filename', '')}"
            media_items.append(MediaItem(
                media_type="image" if att.get("filename", "").endswith((".png", ".jpg", ".jpeg", ".webp")) else "document",
                url=url,
                local_path=att.get("path"),
                alt=att.get("original_name", ""),
            ))
        return InboundMessage(
            channel="phone_web",
            sender="admiral",
            conversation_id=raw_payload.get("thread_id", "default"),
            text=raw_payload.get("prompt", "").strip(),
            media=media_items,
            reply_to=raw_payload.get("reply_to"),
        )


class TelegramChannelAdapter(ChannelAdapter):
    """Encodes OutboundMessage for Telegram Bot API payloads."""

    channel_name: str = "telegram"

    def format_outbound(self, message: OutboundMessage) -> Dict[str, Any]:
        prefix = ""
        if message.semantic_role == "engineering":
            prefix = "🔧 "
        elif message.semantic_role == "alert":
            prefix = "⚠️ "
        elif message.urgency == Urgency.HIGH.value:
            prefix = "⚓ "

        text = f"{prefix}{message.text}"
        payload: Dict[str, Any] = {
            "text": text,
            "parse_mode": "Markdown",
        }

        # Format inline buttons from Actions
        if message.actions:
            inline_keyboard = []
            row = []
            for action in message.actions:
                row.append({"text": action.label, "callback_data": f"action:{action.id}"})
                if len(row) >= 2:
                    inline_keyboard.append(row)
                    row = []
            if row:
                inline_keyboard.append(row)
            payload["reply_markup"] = {"inline_keyboard": inline_keyboard}

        return payload

    def parse_inbound(self, raw_payload: Dict[str, Any]) -> InboundMessage:
        msg = raw_payload.get("message", {})
        sender = "admiral" if str(msg.get("from", {}).get("id")) == str(raw_payload.get("admiral_tg_id", "")) else "external"
        return InboundMessage(
            channel="telegram",
            sender=sender,
            conversation_id=str(msg.get("chat", {}).get("id", "telegram-chat")),
            text=msg.get("text", "") or msg.get("caption", ""),
            media=[],
            reply_to=str(msg.get("reply_to_message", {}).get("message_id")) if "reply_to_message" in msg else None,
            channel_metadata={"message_id": msg.get("message_id")},
        )
