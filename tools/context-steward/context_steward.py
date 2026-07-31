#!/usr/bin/env python3
"""Deterministic, repository-local context checkpoint generator."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "monad.contextSteward.v0.1"
MAX_BYTES = {"current-brief.md": 10_000, "current-state.json": 20_000, "continuation.md": 12_000}
REQUIRED = ("mission", "active_goal", "vocabulary", "established_truth", "next_action", "sources")
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\b(?:sk|AIza)[-_A-Za-z0-9]{20,}\b"),
    re.compile(r"(?i)\b(?:password|secret|api[_-]?key|access[_-]?token)\s*[:=]\s*\S+"),
)
OPTIONAL = ("decisions", "changed_surfaces", "verification", "defects", "deferred_ideas")


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def validate(data: dict, root: Path) -> None:
    missing = [key for key in REQUIRED if not data.get(key)]
    if missing:
        raise ValueError(f"missing required sections: {', '.join(missing)}")
    raw = canonical(data)
    for pattern in SECRET_PATTERNS:
        if pattern.search(raw):
            raise ValueError("possible secret detected; checkpoint refused")
    for source in data["sources"]:
        path = root / source
        if not path.is_file():
            raise ValueError(f"source does not exist: {source}")
    if data.get("schema") != SCHEMA:
        raise ValueError(f"input schema must be {SCHEMA}")


def bullets(items: list[str], fallback: str = "None recorded.") -> str:
    return "\n".join(f"- {item}" for item in items) if items else f"- {fallback}"


def render(data: dict, generated_at: str, digest: str, omitted: list[str]) -> tuple[str, str, dict]:
    source_lines = bullets([f"`{path}`" for path in data["sources"]])
    vocab = bullets([f"**{item['term']}** — {item['meaning']}" for item in data["vocabulary"]])
    brief = f"""# Current context brief

> Compact projection, not project canon. Generated `{generated_at}` from cited
> repository sources. Input digest: `{digest}`.

## Mission

{data['mission']}

## Active course

{data['active_goal']}

## Working vocabulary

{vocab}

## Established truth

{bullets(data['established_truth'])}

## Decisions

{bullets(data.get('decisions', []))}

## Live and changed surfaces

{bullets(data.get('changed_surfaces', []))}

## Verification

{bullets(data.get('verification', []))}

## Known defects

{bullets(data.get('defects', []))}

## Next action

{data['next_action']}

## Deferred ideas

{bullets(data.get('deferred_ideas', []))}

## Source paths

{source_lines}

## Omissions

{bullets(omitted, "None.")}
"""
    continuation = f"""# Fresh-thread continuation packet

Assume Captain role. Continue the Monad project in `{data.get('workspace', str(Path.cwd()))}`.
Read `AGENTS.md`, `CLAUDE.md`, and the cited sources before changing state.

Mission: {data['mission']}

Active goal: {data['active_goal']}

Established truth:
{bullets(data['established_truth'])}

Vocabulary:
{vocab}

Current verification:
{bullets(data.get('verification', []))}

Known defects:
{bullets(data.get('defects', []))}

Immediate next action: {data['next_action']}

Do not silently resume deferred ideas:
{bullets(data.get('deferred_ideas', []))}

Authoritative sources:
{source_lines}

This packet is a generated continuation aid, not canon and not evidence that
the prior conversation was deleted or purged. Digest: `{digest}`.
"""
    state = {
        "schema": SCHEMA,
        "generated_at": generated_at,
        "input_digest": digest,
        "projection": True,
        "active_course": {
            "mission": data["mission"],
            "goal": data["active_goal"],
            "next_action": data["next_action"],
        },
        "established_truth": data["established_truth"],
        "vocabulary": data["vocabulary"],
        "decisions": data.get("decisions", []),
        "changed_surfaces": data.get("changed_surfaces", []),
        "verification": data.get("verification", []),
        "defects": data.get("defects", []),
        "deferred_ideas": data.get("deferred_ideas", []),
        "historical_wake": data.get("historical_wake", []),
        "disposable_repetition_excluded": len(data.get("disposable_repetition", [])),
        "sources": data["sources"],
        "omissions": omitted,
        "limits_bytes": MAX_BYTES,
    }
    return brief, continuation, state


def fit_budget(data: dict, generated_at: str, digest: str) -> tuple[str, str, dict]:
    work = json.loads(json.dumps(data))
    omitted: list[str] = []
    while True:
        brief, continuation, state = render(work, generated_at, digest, omitted)
        encoded = {
            "current-brief.md": brief.encode(),
            "continuation.md": continuation.encode(),
            "current-state.json": (json.dumps(state, indent=2, ensure_ascii=False) + "\n").encode(),
        }
        oversized = [name for name, body in encoded.items() if len(body) > MAX_BYTES[name]]
        if not oversized:
            return brief, continuation, state
        removed = False
        for section in reversed(OPTIONAL):
            values = work.get(section, [])
            if values:
                values.pop()
                if section not in omitted:
                    omitted.append(section)
                removed = True
                break
        if not removed:
            raise ValueError(f"required content exceeds size budget: {', '.join(oversized)}")


def checkpoint(input_path: Path, output_dir: Path, archive: str | None, root: Path) -> None:
    data = json.loads(input_path.read_text())
    validate(data, root)
    normalized = canonical(data)
    source_fingerprints = [
        {
            "path": source,
            "sha256": hashlib.sha256((root / source).read_bytes()).hexdigest(),
        }
        for source in data["sources"]
    ]
    digest_material = canonical({"input": normalized, "sources": source_fingerprints})
    digest = hashlib.sha256(digest_material.encode()).hexdigest()[:16]
    # Stable timestamp follows source content, not wall-clock reruns.
    epoch = max((root / source).stat().st_mtime for source in data["sources"])
    generated_at = datetime.fromtimestamp(epoch, timezone.utc).replace(microsecond=0).isoformat()
    brief, continuation, state = fit_budget(data, generated_at, digest)
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "current-brief.md": brief,
        "continuation.md": continuation,
        "current-state.json": json.dumps(state, indent=2, ensure_ascii=False) + "\n",
    }
    for name, body in outputs.items():
        (output_dir / name).write_text(body)
    if archive:
        safe = re.sub(r"[^a-z0-9-]+", "-", archive.lower()).strip("-")
        stamp = generated_at[:10].replace("-", "")
        archive_path = output_dir / "archive" / f"{stamp}-{safe}-{digest}.md"
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        if archive_path.exists() and archive_path.read_text() != brief:
            raise ValueError(f"immutable archive collision: {archive_path}")
        archive_path.write_text(brief)
    print(json.dumps({"status": "ready", "digest": digest, "generated_at": generated_at, "archive": archive or None}))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("docs/context/checkpoint-input.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("docs/context"))
    parser.add_argument("--archive", metavar="MILESTONE")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    checkpoint(args.input, args.output_dir, args.archive, root)


if __name__ == "__main__":
    main()
