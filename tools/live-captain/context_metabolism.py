"""Small, side-effect-free baseline for continuity-ledger metabolism.

This deliberately does not replace or rewrite the rolling verbatim window.
It models the four operations that a later ledger-maintenance path must prove
safe before it is allowed to edit governing context automatically.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
import re
from typing import Mapping


@dataclass(frozen=True)
class ContinuityFact:
    key: str
    value: str
    source: str
    status: str = "active"

    def __post_init__(self) -> None:
        if not all((self.key.strip(), self.value.strip(), self.source.strip())):
            raise ValueError("continuity facts require key, value, and source")
        if self.status not in {"active", "retired"}:
            raise ValueError("continuity fact status must be active or retired")


@dataclass(frozen=True)
class LedgerEntry:
    section: str
    assertion: str
    source: str


@dataclass(frozen=True)
class LedgerAudit:
    entries: tuple[LedgerEntry, ...]
    missing_source: tuple[str, ...]
    duplicate_assertions: tuple[str, ...]


@dataclass(frozen=True)
class CandidateAssessment:
    candidate: ContinuityFact
    disposition: str
    existing: tuple[ContinuityFact, ...]

    def __post_init__(self) -> None:
        if self.disposition not in {"add", "duplicate", "conflict"}:
            raise ValueError("candidate disposition must be add, duplicate, or conflict")


@dataclass(frozen=True)
class PromotionPolicy:
    """Narrow authority boundary for a possible future ledger writer.

    Keys and source prefixes are explicit capabilities, not suggestions.  An
    empty policy therefore authorizes nothing.
    """

    allowed_keys: frozenset[str] = frozenset()
    trusted_source_prefixes: tuple[str, ...] = ()


@dataclass(frozen=True)
class PromotionDecision:
    candidate: ContinuityFact
    action: str
    reasons: tuple[str, ...]
    assessment: CandidateAssessment

    def __post_init__(self) -> None:
        if self.action not in {"promote", "no_op", "human_review"}:
            raise ValueError("promotion action must be promote, no_op, or human_review")


@dataclass(frozen=True)
class CandidateEnvelope:
    """A candidate whose provenance was checked outside model-authored prose."""

    schema: str
    key: str
    value: str
    evidence_ref: str
    evidence_sha256: str


def ingest_attested_candidate(
    payload: str, attestations: Mapping[str, bytes]
) -> ContinuityFact:
    """Validate a strict candidate envelope against independently supplied bytes.

    ``attestations`` is deliberately an argument rather than content embedded in
    the candidate.  A later caller may populate it from a trusted event store or
    command record; candidate text cannot attest to itself.
    """
    try:
        raw = json.loads(payload)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError("candidate must be valid JSON") from exc
    required = {
        "schema",
        "key",
        "value",
        "evidence_ref",
        "evidence_sha256",
    }
    if not isinstance(raw, dict) or set(raw) != required:
        raise ValueError("candidate envelope has unknown or missing fields")
    if not all(isinstance(raw[field], str) and raw[field].strip() for field in required):
        raise ValueError("candidate envelope fields must be non-empty strings")
    envelope = CandidateEnvelope(**raw)
    if envelope.schema != "live-captain-candidate/v1":
        raise ValueError("unsupported candidate schema")
    evidence = attestations.get(envelope.evidence_ref)
    if evidence is None:
        raise ValueError("candidate evidence is not independently available")
    actual_digest = hashlib.sha256(evidence).hexdigest()
    if envelope.evidence_sha256 != actual_digest:
        raise ValueError("candidate evidence digest mismatch")
    return ContinuityFact(
        envelope.key,
        envelope.value,
        f"attested:{envelope.evidence_ref}#sha256:{actual_digest}",
    )


def audit_ledger(markdown: str) -> LedgerAudit:
    """Audit the real prose ledger without rewriting or interpreting it.

    Entries are top-level Markdown bullets. Continuation lines are retained,
    and the final ``Source:`` marker is treated as provenance. This deliberately
    detects only structural defects; semantic contradiction still requires an
    explicit fact key rather than a guess from prose.
    """
    section = ""
    blocks: list[tuple[str, list[str]]] = []
    current: list[str] | None = None
    current_section = ""
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        if raw_line.startswith("- "):
            if current is not None:
                blocks.append((current_section, current))
            current_section = section
            current = [raw_line[2:].strip()]
        elif current is not None and (raw_line.startswith("  ") or not line):
            if line:
                current.append(line)
        elif current is not None:
            blocks.append((current_section, current))
            current = None
    if current is not None:
        blocks.append((current_section, current))

    entries: list[LedgerEntry] = []
    missing: list[str] = []
    assertions_seen: dict[str, int] = {}
    for entry_section, lines in blocks:
        text = " ".join(lines)
        match = re.search(r"\s+Source:\s+(.+)$", text)
        if match:
            assertion = text[: match.start()].strip()
            source = match.group(1).strip()
        else:
            assertion = text.strip()
            source = ""
            missing.append(assertion)
        entries.append(LedgerEntry(entry_section, assertion, source))
        normalized = " ".join(assertion.casefold().split())
        assertions_seen[normalized] = assertions_seen.get(normalized, 0) + 1

    duplicates = tuple(
        assertion for assertion, count in assertions_seen.items() if count > 1
    )
    return LedgerAudit(tuple(entries), tuple(missing), duplicates)


def consolidate(facts: list[ContinuityFact]) -> list[ContinuityFact]:
    """Remove exact duplicates while retaining distinct provenance."""
    seen: set[tuple[str, str, str, str]] = set()
    result = []
    for fact in facts:
        identity = (fact.key, fact.value, fact.source, fact.status)
        if identity not in seen:
            seen.add(identity)
            result.append(fact)
    return result


def contradictions(facts: list[ContinuityFact]) -> dict[str, list[ContinuityFact]]:
    """Return active keys that currently assert more than one value."""
    by_key: dict[str, list[ContinuityFact]] = {}
    for fact in consolidate(facts):
        if fact.status == "active":
            by_key.setdefault(fact.key, []).append(fact)
    return {
        key: entries
        for key, entries in by_key.items()
        if len({entry.value for entry in entries}) > 1
    }


def assess_candidate(
    facts: list[ContinuityFact], candidate: ContinuityFact
) -> CandidateAssessment:
    """Classify one proposed active fact without changing the supplied facts.

    A key is deliberately required. Unkeyed ledger prose is not interpreted as
    semantic state, and conflicts remain visible for human judgment.
    """
    if candidate.status != "active":
        raise ValueError("only active candidate facts can be assessed")
    existing = tuple(
        fact
        for fact in consolidate(facts)
        if fact.status == "active" and fact.key == candidate.key
    )
    if any(fact.value == candidate.value for fact in existing):
        disposition = "duplicate"
    elif existing:
        disposition = "conflict"
    else:
        disposition = "add"
    return CandidateAssessment(candidate, disposition, existing)


def promotion_decision(
    facts: list[ContinuityFact],
    candidate: ContinuityFact,
    policy: PromotionPolicy = PromotionPolicy(),
) -> PromotionDecision:
    """Decide whether a future writer could promote one assessed candidate.

    This function has no write path.  Promotion is permitted only for a novel
    assertion whose key is explicitly allowlisted, whose provenance begins
    with an explicitly trusted prefix, and whose baseline key is not already
    contradictory.  Duplicates are harmless no-ops.  Conflicts, ambiguity,
    and missing authority always require human review.
    """
    assessment = assess_candidate(facts, candidate)
    if assessment.disposition == "duplicate":
        return PromotionDecision(candidate, "no_op", ("exact active value exists",), assessment)

    reasons: list[str] = []
    if assessment.disposition == "conflict":
        reasons.append("active keyed value conflicts")
    if candidate.key not in policy.allowed_keys:
        reasons.append("key is not explicitly allowlisted")
    if not policy.trusted_source_prefixes or not candidate.source.startswith(
        policy.trusted_source_prefixes
    ):
        reasons.append("source is not explicitly trusted")
    if candidate.key in contradictions(facts):
        reasons.append("baseline key is already contradictory")

    if reasons:
        return PromotionDecision(candidate, "human_review", tuple(reasons), assessment)
    return PromotionDecision(candidate, "promote", ("explicit policy boundary satisfied",), assessment)


def retire(facts: list[ContinuityFact], key: str, value: str) -> list[ContinuityFact]:
    """Retire a specific assertion; never discard its value or provenance."""
    return [
        replace(fact, status="retired")
        if fact.key == key and fact.value == value and fact.status == "active"
        else fact
        for fact in facts
    ]


def retrieve(
    facts: list[ContinuityFact], query: str, *, include_retired: bool = False
) -> list[ContinuityFact]:
    """Retrieve matching facts in stable order using simple explicit terms."""
    terms = {term.casefold() for term in query.split() if term.strip()}
    if not terms:
        return []
    matches = []
    for fact in consolidate(facts):
        if fact.status == "retired" and not include_retired:
            continue
        haystack = f"{fact.key} {fact.value} {fact.source}".casefold()
        if all(term in haystack for term in terms):
            matches.append(fact)
    return matches
