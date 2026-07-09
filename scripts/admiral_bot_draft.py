from __future__ import annotations

from datetime import date
from pathlib import Path


WARNING = "DRAFT ONLY - HUMAN REVIEW REQUIRED - DO NOT PUBLISH DIRECTLY"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def build_dispatch(entries: list[str]) -> str:
    today = date.today().isoformat()
    source_block = "\n".join(f"- {entry}" for entry in entries)
    lead = entries[-1] if entries else "No public-ready entries were available."

    return f"""<!-- {WARNING} -->

# Admiral Bot Draft - {today}

## Draft Dispatch

{lead}

Monad continues under manual review. This draft was generated from public-ready source entries and must be edited by Cameron before any public release.

## Source Entries

{source_block}
"""


def main() -> int:
    root = repo_root()
    source = root / "logs" / "public-ready.log"
    draft_dir = root / "outbox" / "drafts"
    draft_path = draft_dir / f"{date.today().isoformat()}.md"

    if not source.exists():
        print(f"No public-ready log found at {source}. Nothing to draft.")
        return 0

    entries = [line.strip() for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not entries:
        print(f"Public-ready log is empty at {source}. Nothing to draft.")
        return 0

    draft_dir.mkdir(parents=True, exist_ok=True)
    draft_path.write_text(build_dispatch(entries), encoding="utf-8")
    print(f"Draft written to {draft_path}")
    print("DRAFT ONLY - human review required before public release.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
