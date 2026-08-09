# Posture Freeze — Canonical System for Live Captain

**Authority:** Admiral  
**Date:** 2026-08-09  
**Purpose:** Reusable framework for freezing, naming, and restoring operational states  
**Status:** Canonical. Template for all future state captures.

---

## The pattern

When the Admiral needs to preserve an exact operational state across devices or sessions:

### 1. Freeze (by Live Captain)

Capture:
- **Watch posture** (active, read-only, etc.)
- **Frozen work** (what is not changing)
- **Active threads** (what is waiting for Admiral input)
- **Operating principles** (how we're working)
- **Authority record** (who decided what)
- **Capabilities state** (what tools are available)

### 2. Name (by Admiral or Live Captain)

Create a **short, memorable trigger phrase** that encodes the state:
- Two words maximum
- Navigationally clear (MARK, BOOT, HOLD, etc.)
- Active-project or state-specific (RING, WATCH, WII, etc.)
- Easy to type on any device
- Impossible to confuse with other triggers

Examples from practice:
- `MARK RING` — ring-sizing project active, watch posture
- `BOOT [state]` — restart into a frozen configuration
- `HOLD [context]` — maintain current threads and posture

### 3. Canon (by Live Captain)

Write to: `logs/captains/2026/[TRIGGER]-CANONICAL-STATE.md`

Exactly mirror the structure in `2026-08-09_MARK-RING-CANONICAL-STATE.md`:
- Frozen context (what does NOT change)
- Active threads (what IS waiting)
- Operating principles (how we work)
- Authority record (who decided)
- How to restore (one-line instruction)
- What is NOT included (explicit boundaries)

### 4. Restore (by any Claude on any device)

User types: `TRIGGER-PHRASE`

Claude:
1. Reads the canonical state file
2. Recognizes the pattern
3. Restores posture, threads, principles
4. Awaits Admiral input
5. Zero reconstruction, zero drift

---

## Template for future use

```markdown
# [TRIGGER PHRASE] — Canonical operational state

**Authority:** Admiral  
**Date:** [date]  
**Trigger phrase:** `[TRIGGER PHRASE]`  
**Status:** Canonical. Restore to this exact condition on any device, any session.  
**Location:** Gated. Not indexed. Reference only.

---

## Frozen context — do not alter

[Exact state of frozen work, archived items, completed investigations]

**Active watch posture:** [LIVE / READ-ONLY / HOLDING / other]

**Active threads — awaiting Admiral input:**
1. [Thread 1]
2. [Thread 2]
etc.

**Operating principles:**
- [Principle 1]
- [Principle 2]
etc.

**Authority record:**
- [Who did what]

**Capabilities state:**
- [What tools, what limits]

---

## How to restore this state

Type or say: `[TRIGGER PHRASE]`

Claude will read this file, recognize the canonical state, and resume from exactly this condition.

---

## What is NOT included in this state

[Explicit list of what remains unchanged, not re-derived, not re-evaluated]
```

---

## Active registry

Current canonical states:
- `MARK RING` → `logs/captains/2026/2026-08-09_MARK-RING-CANONICAL-STATE.md`

Future states will be added as created, maintaining the same structure.

---

## Standing instructions

1. **Only the Admiral can authorize a freeze.** Live Captain executes.
2. **Trigger phrases are permanent once canonized.** No reuse, no renaming.
3. **Canonical files are gated.** Not in the public corpus.
4. **The template structure is never altered.** New states follow the same format.
5. **Restoration is exact.** No interpretation, no flexibility, no reconstruction.

---

## Why this matters

The Admiral moves between devices, sessions, and work contexts. The Live Captain needs to hand off state without loss of continuity. Canonical posture freezes solve that problem with one short command that works across any device, any session, any Claude instance.

The system is reusable, scalable, and auditable. Every frozen state has provenance. Every trigger is memorable. Every restoration is exact.

🫡⚓
