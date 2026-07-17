#!/usr/bin/env python3
"""Agent Registry V0.1 -- builds a real per-agent activity record from
docs/engineering-orders/packets/*.md, the one place this repo already
records "who did this work" in a structured, consistent way (Master
Packet §13's nine-field shape, §8 "Assigned actor" / §9 "Evidence and
completion state").

Deliberately NOT derived from git authorship: every commit in this repo
is authored as the same local git identity regardless of which agent
(Claude, Codex) actually made it (confirmed by inspection -- `git log
--format='%an <%ae>'` shows one human identity across hundreds of
commits from both agents). The packets' own self-declared "Assigned
actor" text is the only reliable per-agent signal that exists, so this
registry is built from that, not invented or inferred from commit
metadata that can't actually distinguish agents.

See docs/architecture/agent-registry-v0.1.md for scope.
"""
from __future__ import annotations

import datetime
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PACKETS_DIR = os.path.join(ROOT, "docs", "engineering-orders", "packets")
OUTPUT_PATH = os.path.join(ROOT, "docs", "reports", "2026-07-17-agent-registry.md")

# Files in packets/ that are process documentation, not a real work
# record -- excluded from the registry itself, not silently miscounted
# as an empty/unassigned packet.
NON_PACKET_FILES = {"README.md", "template-refused.md"}

KNOWN_ACTORS = ("Claude", "Codex", "Lieutenant")

NUMBERED_SECTION_RE = re.compile(r"^\d+\.\s+\*\*(.+?)\*\*", re.MULTILINE)
H2_SECTION_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)
H1_TITLE_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)


def extract_sections(text: str) -> dict[str, str]:
    """Split a packet into {section_name: body_text}, tolerating both
    formatting conventions actually found in packets/ -- the current
    "N. **Section**" numbered-list style (29 of 35 files) and the older
    "## Section" style (5 of 35). Whichever produces more than one
    section wins; a packet using neither yields an empty dict rather
    than a guess."""
    numbered_matches = list(NUMBERED_SECTION_RE.finditer(text))
    h2_matches = list(H2_SECTION_RE.finditer(text))
    matches = numbered_matches if len(numbered_matches) >= len(h2_matches) else h2_matches
    sections: dict[str, str] = {}
    for i, m in enumerate(matches):
        name = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[name] = text[start:end].strip()
    return sections


def find_section(sections: dict[str, str], *name_fragments: str) -> str:
    for name, body in sections.items():
        lowered = name.lower()
        if any(frag.lower() in lowered for frag in name_fragments):
            return body
    return ""


def detect_actors(assigned_text: str) -> list[str]:
    found = [name for name in KNOWN_ACTORS if re.search(rf"\b{name}\b", assigned_text)]
    return found or ["unspecified"]


# Distinctive multi-word phrases, safe to search anywhere in the section
# text -- specific enough that they're very unlikely to appear describing
# something *other* than this packet's own terminal state. First match
# (by position in text) wins among these.
STRONG_COMPLETION_PATTERNS = (
    ("verification pending", "in-progress"),
    ("verified complete", "complete"),
    ("repository implementation complete", "complete"),
    ("repository wiring verified", "complete"),
    ("complete and recorded", "complete"),
    ("landed in commit", "complete"),
)

# Single common words -- real false positives found by inspecting this
# exact report before trusting it: "claimed" matched inside "was NOT left
# claimed mid-work" (DOCTRINE-001, describing a *different* packet's good
# discipline), and an earlier version of this list included "refused",
# which matched DOCTRINE-001 citing ENG1-REFUSED.md as an example.
# Restricted to the section's own opening (right after the heading, where
# a real terminal-state word actually appears in this repo's convention)
# rather than a full-text search, which is where both false positives
# came from.
WEAK_PREFIX_PATTERNS = (
    ("succeeded", "complete"),
    ("claimed", "in-progress"),
    ("building", "in-progress"),
    ("executing", "in-progress"),
    ("authorized", "queued"),
    ("assigned", "queued"),
)
WEAK_PREFIX_WINDOW = 60


def detect_completion(sections: dict[str, str]) -> str:
    combined = find_section(sections, "evidence", "completion state")
    if not combined:
        return "unknown"
    # Section bodies conventionally open with "-- <state>." right after the
    # heading (an em-dash/double-hyphen separator, not part of the word),
    # so strip leading punctuation/whitespace before matching -- otherwise
    # "-- Complete." never matches a startswith("complete") check.
    lowered = re.sub(r"^[\s—\-–:.]+", "", combined.lower())
    if lowered.startswith("complete") or lowered.startswith("done"):
        return "complete"
    for phrase, status in STRONG_COMPLETION_PATTERNS:
        if phrase in lowered:
            return status
    prefix = lowered[:WEAK_PREFIX_WINDOW]
    for phrase, status in WEAK_PREFIX_PATTERNS:
        if phrase in prefix:
            return status
    # No recognized terminal marker -- true of a handful of older,
    # bullet-list-evidence packets (no prose "Completion state:" line at
    # all). Reporting "unknown" here is the honest outcome, not a bug to
    # paper over with a more aggressive heuristic that would just be a
    # guess dressed up as a classification.
    return "unknown"


def git_first_last_touch(path: str) -> tuple[str | None, str | None]:
    def run(extra_args):
        try:
            result = subprocess.run(
                ["git", "-C", ROOT, "log", "--follow", "--format=%aI"] + extra_args + ["--", path],
                capture_output=True, text=True, timeout=10, check=True,
            )
            lines = [line for line in result.stdout.splitlines() if line.strip()]
            return lines
        except (OSError, subprocess.SubprocessError):
            return []

    lines = run([])
    if not lines:
        return None, None
    return lines[-1], lines[0]  # git log is newest-first; last line is oldest (first touch)


def build_registry() -> dict:
    packet_files = sorted(
        f for f in os.listdir(PACKETS_DIR)
        if f.endswith(".md") and f not in NON_PACKET_FILES
    )

    packets = []
    for filename in packet_files:
        path = os.path.join(PACKETS_DIR, filename)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        title_match = H1_TITLE_RE.search(text)
        title = title_match.group(1).strip() if title_match else filename
        sections = extract_sections(text)
        assigned_text = find_section(sections, "assigned actor")
        actors = detect_actors(assigned_text)
        completion = detect_completion(sections)
        is_refused = "REFUSED" in filename.upper() or "[REFUSED]" in title.upper()
        first_touch, last_touch = git_first_last_touch(os.path.relpath(path, ROOT))
        packets.append({
            "filename": filename,
            "title": title,
            "actors": actors,
            "assigned_text": assigned_text,
            "completion": "refused" if is_refused else completion,
            "first_touch": first_touch,
            "last_touch": last_touch,
        })

    registry: dict[str, dict] = {}
    for actor in KNOWN_ACTORS + ("unspecified",):
        registry[actor] = {"packets": [], "complete": 0, "in_progress": 0, "queued": 0, "refused": 0, "unknown": 0}

    for packet in packets:
        for actor in packet["actors"]:
            registry.setdefault(actor, {"packets": [], "complete": 0, "in_progress": 0, "queued": 0, "refused": 0, "unknown": 0})
            registry[actor]["packets"].append(packet)
            key = packet["completion"].replace("-", "_")
            registry[actor][key] = registry[actor].get(key, 0) + 1

    return {"generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "packets": packets, "registry": registry}


def render_markdown(data: dict) -> str:
    lines = []
    lines.append("# Agent Registry")
    lines.append("")
    lines.append(f"Generated: {data['generated_at']}")
    lines.append("")
    lines.append(
        "Built from `docs/engineering-orders/packets/*.md`'s own self-declared "
        "`Assigned actor` / `Evidence and completion state` fields (Master Packet "
        "§13) -- **not** from git authorship, which cannot distinguish agents in "
        "this repo (every commit shares one local git identity regardless of "
        "which agent made it, confirmed by inspection). See "
        "`docs/architecture/agent-registry-v0.1.md` for the full design and what's "
        "deliberately not attempted here (cost tracking, tool-access enforcement, "
        "memory rules -- none of these have a real, non-fabricated data source yet)."
    )
    lines.append("")

    total_packets = len(data["packets"])
    lines.append(f"**{total_packets} packets on record.**")
    lines.append("")

    for actor in ("Claude", "Codex", "Lieutenant", "unspecified"):
        info = data["registry"].get(actor)
        if not info or not info["packets"]:
            continue
        lines.append(f"## {actor}")
        lines.append("")
        lines.append(
            f"{len(info['packets'])} packet(s) — "
            f"{info.get('complete', 0)} complete, "
            f"{info.get('in_progress', 0)} in progress, "
            f"{info.get('queued', 0)} queued, "
            f"{info.get('refused', 0)} refused, "
            f"{info.get('unknown', 0)} unknown status."
        )
        lines.append("")
        lines.append("| Packet | Status | First recorded | Last touched |")
        lines.append("|---|---|---|---|")
        for packet in sorted(info["packets"], key=lambda p: p["last_touch"] or "", reverse=True):
            first = (packet["first_touch"] or "—")[:10]
            last = (packet["last_touch"] or "—")[:10]
            lines.append(f"| {packet['title']} | {packet['completion']} | {first} | {last} |")
        lines.append("")

    lines.append("## What this registry does not cover")
    lines.append("")
    lines.append(
        "- **Cost/spend per agent.** No cross-system ledger exists (see "
        "`docs/reports/2026-07-15-feature-matrix.md`'s `CT-01` row, still true). "
        "The one real spend ledger in this repo, `data/voice-engine/voice.sqlite3`'s "
        "`spend` table, is scoped to voice generation specifically, not per-agent, "
        "and empty at last check."
    )
    lines.append(
        "- **Enforced tool-access / authority envelopes.** Packets document scope "
        "and exclusions in prose (e.g. \"Bot 1 owns radio-console files\"), which "
        "humans and agents are expected to honor -- there's no runtime mechanism "
        "that actually prevents a violation."
    )
    lines.append(
        "- **Memory rules.** Doesn't apply the way it does to in-fiction Living "
        "Fleet captains; not attempted here."
    )
    lines.append(
        "- **Work-queue-only tasks** (`docs/engineering-orders/queue.md`) that "
        "never became a full packet -- by design, per `packets/README.md`'s own "
        "distinction between the two (\"synthesis, verification, or documentation "
        "with no runtime/repository-state change\" doesn't need a packet)."
    )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    data = build_registry()
    markdown = render_markdown(data)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(markdown)
    print(f"Wrote {OUTPUT_PATH} ({len(data['packets'])} packets, {sum(1 for a in data['registry'] if data['registry'][a]['packets'])} actors)")


if __name__ == "__main__":
    sys.exit(main())
