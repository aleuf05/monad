#!/usr/bin/env python3
"""M³ cycle v0.1 — the tri-condition axiom, evaluated over this repo's own docs.

Per MSIR-M3-Q1 (answered A, 2026-08-05): D_t is the document corpus under
docs/, and H_t is git. A transition Δ_t is therefore a proposed change to
that corpus, and the two states being compared are:

    M_t      = docs/ as committed at HEAD
    M_{t+1}  = docs/ as it stands in the working tree

which makes commit and rollback literally `git commit` and
`git checkout --`. Nothing here reimplements content-addressed history:
§IV's "State Drift Interlock" describes approximately what git already
does, so git does it.

The predicates below are deliberately crude. They are also real -- each
one reads something actually present in the corpus rather than standing
in for a measurement that hasn't been defined. Crude and checkable beats
elegant and abstract for a first cycle; MSIR-M3-NUCLEAR-PACKET-02 §II
names Cont, V, and Q_rev without making any of them computable, and this
is the smallest honest way to make them so.

Two deliberate departures from that packet, following MSR-EXP-001's own
refinements (§4.1 and §4.2), which the packet regressed on:

  * Reachability is valued, not merely expanded. Requiring R_t ⊊ R_{t+1}
    would forbid ever removing a hazard from the corpus.
  * Q_rev is a vector under constrained improvement, not a scalar. A
    scalar lets the corpus get better at generating documents while
    getting worse at verifying them, and report that as progress.
"""

from __future__ import annotations

import io
import re
import subprocess
import tarfile
from pathlib import Path

DOCS_PREFIX = "docs/"

LINK_PATTERN = re.compile(r"\[\[([^\]]+)\]\]")
TITLE_PATTERN = re.compile(r"^#\s+(.+)$", re.MULTILINE)

# Q_rev components whose degradation is never acceptable, however much
# the others improve. These are the capacities that make a bad revision
# survivable; trading them for throughput is the failure mode the vector
# form exists to catch.
PROTECTED = ("verify", "govern", "recover")


class CycleError(RuntimeError):
    pass


def _git(repo: Path, *args: str, binary: bool = False):
    result = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, timeout=90,
        text=not binary,
    )
    if result.returncode != 0:
        err = result.stderr if not binary else result.stderr.decode("utf-8", "replace")
        raise CycleError(f"git {' '.join(args)}: {err.strip()}")
    return result.stdout


def corpus_at_head(repo: Path) -> dict[str, str]:
    """docs/ as committed. One `git archive` rather than a subprocess per
    file -- 146 documents makes that difference visible."""
    blob = _git(repo, "archive", "HEAD", DOCS_PREFIX, binary=True)
    out: dict[str, str] = {}
    with tarfile.open(fileobj=io.BytesIO(blob)) as tar:
        for member in tar.getmembers():
            if not member.isfile() or not member.name.endswith(".md"):
                continue
            handle = tar.extractfile(member)
            if handle is None:
                continue
            out[member.name] = handle.read().decode("utf-8", "replace")
    return out


def corpus_at_worktree(repo: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for path in (repo / "docs").rglob("*.md"):
        rel = str(path.relative_to(repo))
        try:
            out[rel] = path.read_text(encoding="utf-8")
        except OSError:
            continue
    return out


# --- V: valuation of the lawfully reachable future -------------------------

def valuation(corpus: dict[str, str]) -> dict:
    """What futures does this corpus lawfully permit, and how good are they?

    For a corpus of documents, "reachable future" is read as: what can a
    reader or a later session actually *do* from here. Connectivity makes
    navigation possible; stated reversal conditions make reconsideration
    possible; epistemic labels make trust calibration possible; unresolved
    staged material subtracts, because it is a claim not yet judged.
    """
    titles = set()
    for text in corpus.values():
        match = TITLE_PATTERN.search(text)
        if match:
            titles.add(_norm(match.group(1)))
    stems = {Path(p).stem.lower() for p in corpus}

    resolvable = 0
    dangling = 0
    for text in corpus.values():
        for link in LINK_PATTERN.findall(text):
            if _norm(link) in titles or _norm(link) in stems:
                resolvable += 1
            else:
                dangling += 1

    reversible = sum(1 for t in corpus.values() if "what would change the answer" in t.lower())
    labelled = sum(1 for t in corpus.values() if "epistemic label" in t.lower())
    staged = sum(1 for t in corpus.values() if "staged, awaiting evaluation" in t.lower())

    components = {
        "connectivity": resolvable,
        "reversibility": reversible * 3,
        "auditability": labelled * 2,
        "dangling_links": -dangling,
        "unresolved_staged": -staged * 2,
    }
    return {"total": sum(components.values()), "components": components,
            "documents": len(corpus)}


# --- Q_rev: revision-capacity vector ---------------------------------------

def q_rev(corpus: dict[str, str]) -> dict[str, int]:
    """The six capacities from MSR-EXP-001 §4.2, each counted from something
    the corpus actually contains rather than asserted."""
    def count(predicate) -> int:
        return sum(1 for path, text in corpus.items() if predicate(path, text.lower()))

    return {
        # capacity to generate candidate transformations: open questions
        # and queued work are where proposals come from
        "gen": count(lambda p, t: "/queries/" in p or p.endswith("queue.md")),
        # capacity to model consequences: documents describing the system
        "model": count(lambda p, t: "/doctrine/" in p),
        # capacity to test before commitment: stated acceptance criteria
        "test": count(lambda p, t: "acceptance criteria" in t or "what counts as a sufficient" in t),
        # capacity to verify invariants: recorded evidence
        "verify": count(lambda p, t: "evidence" in t or "verified starting state" in t),
        # capacity to govern acceptance/rejection: refusals and doctrine
        "govern": count(lambda p, t: "[refused]" in t or "/doctrine/" in p),
        # capacity to recover from a bad revision: stated reversal conditions
        "recover": count(lambda p, t: "what would change the answer" in t or "rollback" in t),
    }


def constrained_improvement(before: dict[str, int], after: dict[str, int]) -> dict:
    """`≻`, not `>`: at least one capacity must rise, and no protected
    capacity may fall. A single scalar would let the first happen while
    concealing the second."""
    deltas = {k: after[k] - before.get(k, 0) for k in after}
    regressed = [k for k in PROTECTED if deltas.get(k, 0) < 0]
    improved = [k for k, v in deltas.items() if v > 0]
    return {
        "deltas": deltas,
        "improved": improved,
        "protected_regressed": regressed,
        "holds": bool(improved) and not regressed,
    }


# --- Cont: accountable continuity ------------------------------------------

def continuity(head: dict[str, str], work: dict[str, str], repo: Path) -> dict:
    """Cont = I ∧ T ∧ R ∧ G, each with a stated reason when it fails."""
    reasons: dict[str, list[str]] = {"I": [], "T": [], "R": [], "G": []}

    # I -- identity: a document that survives the transition keeps its
    # identity. A retitled file is a new document wearing an old name.
    for path, before in head.items():
        after = work.get(path)
        if after is None:
            reasons["I"].append(f"{path}: removed from the corpus")
            continue
        before_title = TITLE_PATTERN.search(before)
        after_title = TITLE_PATTERN.search(after)
        if before_title and after_title and _norm(before_title.group(1)) != _norm(after_title.group(1)):
            reasons["I"].append(f"{path}: title changed")

    # T -- traceability: HEAD must be a real commit with a resolvable
    # lineage for the transition to be attributable at all.
    try:
        _git(repo, "rev-parse", "--verify", "HEAD")
    except CycleError:
        reasons["T"].append("HEAD does not resolve; no lineage to append to")

    # R -- recoverability: every modified document must already be tracked,
    # so `git checkout --` restores it exactly. Untracked additions are
    # recoverable by deletion and so do not threaten R.
    status = _git(repo, "status", "--porcelain", "--", "docs")
    for line in status.splitlines():
        code, _, name = line[:2], line[2:3], line[3:]
        if code.strip() == "??":
            continue
        if code.strip() in {"M", "D", "R", "MM", "AM"} and name not in head:
            reasons["R"].append(f"{name}: modified but not present at HEAD")

    # G -- governance: this repo's own rules, the ones that are checkable.
    # Doctrine 013 §3.3 is the load-bearing one -- a refusal that can be
    # rewritten stops being a record.
    for path, before in head.items():
        if "/packets/" not in path or "REFUSED" not in path.upper():
            continue
        after = work.get(path)
        if after is None:
            reasons["G"].append(f"{path}: refusal deleted (doctrine 013 §3.3)")
        elif not after.startswith(before.rstrip() [:len(before.rstrip())]) and before.rstrip() not in after:
            reasons["G"].append(f"{path}: refusal content rewritten rather than appended (doctrine 013 §3.3)")

    flags = {k: not v for k, v in reasons.items()}
    return {
        "I": flags["I"], "T": flags["T"], "R": flags["R"], "G": flags["G"],
        "holds": all(flags.values()),
        "reasons": {k: v for k, v in reasons.items() if v},
    }


# --- the cycle -------------------------------------------------------------

def evaluate(repo: Path) -> dict:
    """One full evaluation of Δ_t. Returns a verdict, never applies it."""
    head = corpus_at_head(repo)
    work = corpus_at_worktree(repo)

    changed = sorted(
        {p for p in set(head) | set(work) if head.get(p) != work.get(p)}
    )
    if not changed:
        return {"proposed": False, "changed": [], "verdict": "no-op",
                "detail": "docs/ is identical to HEAD; there is no Δ_t to evaluate"}

    cont = continuity(head, work, repo)
    v_before, v_after = valuation(head), valuation(work)
    q_before, q_after = q_rev(head), q_rev(work)
    q = constrained_improvement(q_before, q_after)

    value_holds = v_after["total"] > v_before["total"]
    holds = cont["holds"] and value_holds and q["holds"]

    return {
        "proposed": True,
        "changed": changed,
        "continuity": cont,
        "valuation": {
            "before": v_before["total"], "after": v_after["total"],
            "holds": value_holds,
            "components_before": v_before["components"],
            "components_after": v_after["components"],
        },
        "q_rev": {"before": q_before, "after": q_after, **q},
        "verdict": "commit" if holds else "rollback",
        "documents": len(work),
    }


def commit(repo: Path, message: str) -> dict:
    _git(repo, "add", "--", "docs")
    _git(repo, "commit", "-m", message)
    return {"ok": True, "commit": _git(repo, "rev-parse", "--short", "HEAD").strip()}


def rollback(repo: Path) -> dict:
    """B_t: restore the exact state prior to the proposal. Tracked files are
    reverted; untracked additions are left alone rather than deleted, since
    destroying unreviewed work is a worse failure than an incomplete
    rollback."""
    _git(repo, "checkout", "--", "docs")
    return {"ok": True, "restored": True}


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
