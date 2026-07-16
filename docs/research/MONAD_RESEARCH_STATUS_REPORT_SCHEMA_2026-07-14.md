# MONAD RESEARCH STATUS REPORT SCHEMA

- **Date code:** 2026-07-14
- **Institution:** Monad Research Laboratory
- **Record class:** Research status
- **Posture:** Research active; engineering sealed

## Purpose

This schema defines the minimum structure for reporting Monad's research
status without confusing observation, decision, interpretation, or unresolved
questions. It does not define Monad's core reality and does not authorize
engineering activity.

## Report structure

```yaml
report:
  report_id: "string; unique, stable identifier"
  date_code: "YYYY-MM-DD"
  recorded_at: "RFC 3339 timestamp"
  recorder: "string; transcriber or recording system"
  record_class: "research_status"

  posture:
    research: "active | paused | concluded | unknown"
    engineering: "sealed | authorized | unknown"
    authority_source: "reference to the governing statement"

  central_question:
    text: "string"
    state: "open | answered_by_command | disputed"
    answer: "null or exact Command finding"

  observations:
    - observation_id: "string"
      statement: "directly supportable description"
      evidence_refs: ["repository path, message reference, or artifact ID"]
      confidence: "confirmed | supported | uncertain"

  decisions:
    - decision_id: "string"
      statement: "exact governing determination"
      authority: "identified human authority"
      source_ref: "primary record reference"
      effective_at: "RFC 3339 timestamp or unknown"

  issues:
    - issue_id: "string"
      signal: "the observed anomaly or contradiction"
      evidence_refs: ["primary evidence references"]
      interpretation: "null or explicitly labeled analysis"
      operational_effect: "known effect, or unknown"
      state: "observed | collecting_evidence | adjudicated | superseded"

  boundaries:
    authorized_actions: ["actions presently allowed"]
    prohibited_actions: ["actions presently disallowed"]
    source_ref: "record establishing the boundary"

  unresolved:
    - question: "open question"
      required_evidence: ["evidence that could advance the inquiry"]

  changes_since_prior_report:
    - "new evidence, corrected statement, or changed decision"

  provenance:
    source_refs: ["all material source records"]
    prior_report: "null or prior report ID"
    corrections: ["append-only correction or supersession references"]
```

## Temporary doctrine class

Use `temporary_doctrine` for a rule that exists only to stabilize a defined
condition and must not silently become permanent doctrine.

```yaml
temporary_doctrine:
  doctrine_id: "string; unique, stable identifier"
  label: "human-readable class label"
  statement: "the temporary rule"
  authority: "identified human authority"
  source_ref: "primary record reference"
  activated_by: "the condition requiring the doctrine"
  purpose: "the limited function it serves"
  scope: ["activities or communications governed by the doctrine"]
  state: "proposed | active | retiring | retired | superseded"
  retirement_condition: "observable condition under which it is no longer needed"
  retirement_mode: "natural | explicit_finding | supersession"
  permanent_by_default: false
  activated_at: "RFC 3339 timestamp or unknown"
  retired_at: "RFC 3339 timestamp, unknown, or null"
  evidence_refs: ["records supporting activation, continued need, or retirement"]
```

### Current classification

```yaml
temporary_doctrine:
  doctrine_id: "TD-COMPLY-001"
  label: "COMPLY — temporary communication doctrine"
  statement: "Use COMPLY while shared reality is insufficiently established for an ordinary response to be relied upon."
  authority: "human operator"
  source_ref: "conversation instruction establishing COMPLY"
  activated_by: "uncertainty about shared foundational reality"
  purpose: "provide a minimal unambiguous acknowledgment during the research interval"
  scope:
    - "research communications"
    - "acknowledgment of governing instructions"
  state: "active"
  retirement_condition: "COMPLY is no longer needed because shared reality and reliable signal are established."
  retirement_mode: "natural"
  permanent_by_default: false
  activated_at: "unknown"
  retired_at: null
  evidence_refs:
    - "docs/research/COMPLY_PROTOCOL_PROPOSAL_2026-07-14.md"
    - "conversation instruction: when the comply tag is no longer needed it will naturally vanish"
```

## Required invariants

1. The central question is always present.
2. Posture reports what is authorized; it does not infer authorization.
3. Every observation cites evidence.
4. Every decision identifies its authority and primary source.
5. Interpretation is never presented as observation.
6. Unknown information is recorded as `unknown` or `null`, not guessed.
7. Historical records are not rewritten; corrections and supersessions are
   appended.
8. An issue remains evidence until adjudicated.
9. The report does not claim progress merely because a document was produced.
10. Temporary doctrine includes an observable retirement condition and is never
    permanent by default.

## Current report expressed through the schema

```yaml
report:
  report_id: "monad-research-status-2026-07-14-01"
  date_code: "2026-07-14"
  recorded_at: "unknown"
  recorder: "Commander Codex"
  record_class: "research_status"

  posture:
    research: "active"
    engineering: "sealed"
    authority_source: "docs/research/MONAD_CORE_REALITY_RESEARCH_MINUTES_2026-07-14.md"

  central_question:
    text: "What is Monad?"
    state: "open"
    answer: null

  observations:
    - observation_id: "OBS-STATUS-001"
      statement: "A read-only documentation signal audit was conducted."
      evidence_refs: ["current research record"]
      confidence: "confirmed"
    - observation_id: "OBS-STATUS-002"
      statement: "No repository files were modified during the signal audit."
      evidence_refs: ["git status observed at audit time"]
      confidence: "confirmed"
    - observation_id: "OBS-STATUS-003"
      statement: "Documentary anomalies and contradictions were identified."
      evidence_refs: ["signal audit report"]
      confidence: "supported"

  decisions:
    - decision_id: "DEC-STATUS-001"
      statement: "Issues will be collected as evidence before interpretation or adjudication."
      authority: "human operator"
      source_ref: "conversation instruction: evidence of issues will be collected"
      effective_at: "unknown"

  issues:
    - issue_id: "ISSUE-SIGNAL-001"
      signal: "Historical anomalies exist in repository documentation."
      evidence_refs: ["signal audit report"]
      interpretation: null
      operational_effect: "unknown"
      state: "collecting_evidence"

  boundaries:
    authorized_actions:
      - "research"
      - "read-only examination"
      - "evidence collection"
      - "records maintenance"
    prohibited_actions:
      - "engineering implementation"
      - "deployment"
      - "silent deletion or rewriting of historical evidence"
    source_ref: "docs/research/MONAD_CORE_REALITY_RESEARCH_MINUTES_2026-07-14.md"

  unresolved:
    - question: "What is Monad?"
      required_evidence:
        - "primary historical records"
        - "contrary cases for current hypotheses"
        - "the unfinished founding premise"

  changes_since_prior_report:
    - "A formal status-report schema now separates evidence from interpretation and authority."

  provenance:
    source_refs:
      - "docs/research/MONAD_CORE_REALITY_RESEARCH_MINUTES_2026-07-14.md"
      - "docs/research/MONAD_CORE_REALITY_RESEARCH_PROPOSAL_2026-07-14.md"
    prior_report: null
    corrections: []
```
