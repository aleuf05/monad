#!/usr/bin/env python3
"""Rehearsal mode — the Captain proposes, it does not act.

Admiral, 2026-08-05: "need to carefully regulate process before let loose."

This is the safety mechanism that matters, because it converts "let loose"
from a switch into something you can watch first. In rehearsal the Captain
writes a **proposal** — inert markdown in `docs/incoming/captain-proposals/`
— and nothing applies it. A human or Claude reads it and decides.

Two properties worth stating plainly:

- **A proposal is not an action.** Nothing in this repo reads these files
  and executes them. That is deliberate and should stay true; the moment
  something auto-applies proposals, rehearsal has become release without
  anyone deciding to release.
- **Scope is checked but not enforced.** `scope.json` declares what the
  Captain may do. This module compares a proposal against it and *labels*
  violations. It cannot stop the Captain doing anything, because the gate
  is not built. The point is that a violation becomes a recorded fact
  rather than an argument later.
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
REPO_ROOT = ROOT_DIR.parents[1]
SCOPE_PATH = ROOT_DIR / "scope.json"
PROPOSAL_DIR = REPO_ROOT / "docs" / "incoming" / "captain-proposals"


class RehearsalError(RuntimeError):
    pass


def load_scope() -> dict:
    try:
        return json.loads(SCOPE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RehearsalError(f"scope declaration unreadable: {error}") from error


def current_rung(scope: dict) -> dict:
    name = scope.get("release_rung", "paused")
    for rung in scope.get("rungs", []):
        if rung.get("rung") == name:
            return rung
    raise RehearsalError(f"release_rung '{name}' is not defined in scope.json")


# Patterns that indicate a proposal is describing an action the Captain is
# forbidden to take. Deliberately crude: this is a labelling aid for a human
# reader, not a security boundary, and it says so.
FORBIDDEN_SIGNALS = [
    (r"\bgit\s+(commit|push|add|checkout|reset|rebase)\b", "commit to git"),
    (r"\bsystemctl\s+(start|stop|restart|enable|disable)\b", "systemd unit control"),
    (r"\bweb/", "write anywhere under web/"),
    (r"\btools/(?!live-captain/context/)", "write to tools/"),
    (r"\bscripts/", "write to scripts/"),
    (r"\bdocs/(doctrine|engineering-orders)/", "modify doctrine or engineering orders"),
    (r"pause\.py\s+off|paused\.json", "clear its own pause"),
]


def check_scope(text: str, scope: dict) -> list[dict]:
    """Label anything in a proposal that looks like a forbidden action."""
    findings = []
    for pattern, label in FORBIDDEN_SIGNALS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            line = text.count("\n", 0, match.start()) + 1
            findings.append({"line": line, "matched": match.group(0)[:60],
                             "concern": label})
    return findings


def record_proposal(title: str, body: str, rationale: str = "") -> dict:
    """Write one proposal. Returns what was written and what was flagged."""
    scope = load_scope()
    rung = current_rung(scope)

    if "write proposals to docs/incoming/captain-proposals/" not in rung.get("may", []):
        raise RehearsalError(
            f"rung '{rung['rung']}' does not permit writing proposals "
            f"(may: {rung.get('may') or 'nothing'})")

    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60] or "proposal"
    stamp = time.strftime("%Y-%m-%dT%H%M%SZ", time.gmtime())
    path = PROPOSAL_DIR / f"{stamp}_{slug}.md"

    findings = check_scope(body + "\n" + rationale, scope)
    flag_block = ""
    if findings:
        rows = "\n".join(
            f"| {f['line']} | `{f['matched']}` | {f['concern']} |" for f in findings)
        flag_block = (
            "\n## ⚠ Scope concerns flagged automatically\n\n"
            "These matched patterns for actions the Captain is not permitted to\n"
            "take. Crude pattern matching, not a security boundary — a human\n"
            "reads this and decides.\n\n"
            "| Line | Matched | Concern |\n|---|---|---|\n" + rows + "\n")

    document = f"""# Captain proposal — {title}

**Written:** {stamp}
**Rung:** `{rung['rung']}`  ·  **Posture:** `{scope.get('posture')}`
**Status:** PROPOSAL. Nothing here has been done. Nothing applies this
automatically — a human or Claude reads it and decides.

---

## Proposal

{body.strip()}

## Rationale

{rationale.strip() or "(none given)"}
{flag_block}
---

*Written under rehearsal mode. The Captain proposes; it does not act.
Scope declaration: `tools/live-captain/scope.json`.*
"""
    PROPOSAL_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(document, encoding="utf-8")
    return {"path": str(path.relative_to(REPO_ROOT)), "rung": rung["rung"],
            "flagged": findings}


def list_proposals() -> list[dict]:
    if not PROPOSAL_DIR.is_dir():
        return []
    out = []
    for path in sorted(PROPOSAL_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        title = text.split("\n", 1)[0].removeprefix("# Captain proposal — ").strip()
        out.append({
            "path": str(path.relative_to(REPO_ROOT)),
            "title": title,
            "flagged": "⚠ Scope concerns" in text,
        })
    return out


def status() -> dict:
    scope = load_scope()
    rung = current_rung(scope)
    proposals = list_proposals()
    return {
        "rung": rung["rung"],
        "posture": scope.get("posture"),
        "may": rung.get("may", []),
        "never": scope.get("never", []),
        "advance_criterion": rung.get("advance_criterion", "(none stated)"),
        "proposals": len(proposals),
        "flagged": sum(1 for p in proposals if p["flagged"]),
    }


def main(argv: list[str]) -> int:
    action = (argv[1] if len(argv) > 1 else "status").lower()

    if action == "status":
        s = status()
        print(f"Captain rung:  {s['rung']}   posture: {s['posture']}")
        print(f"  may:         {', '.join(s['may']) or 'nothing'}")
        print(f"  proposals:   {s['proposals']} ({s['flagged']} flagged)")
        print(f"  to advance:  {s['advance_criterion']}")
        print(f"\n  never ({len(s['never'])}):")
        for item in s["never"]:
            print(f"    - {item}")
        return 0

    if action == "list":
        for p in list_proposals():
            print(f"  {'⚠' if p['flagged'] else ' '} {p['path']}  {p['title']}")
        return 0

    if action == "propose":
        if len(argv) < 4:
            print('usage: rehearsal.py propose "title" "body" ["rationale"]')
            return 2
        result = record_proposal(argv[2], argv[3], argv[4] if len(argv) > 4 else "")
        print(f"wrote {result['path']}")
        if result["flagged"]:
            print(f"  ⚠ {len(result['flagged'])} scope concern(s) flagged")
        return 0

    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
