# Stable Live Trigger — Boot and Push-to-Talk Protocol

**Date:** 2026-08-05  
**State:** Implemented; automated verification passed; human audio acceptance pending  
**Operational hold:** Live Captain autonomous turns remain paused by Admiral order

## Finding

The stable trigger is not an always-restored microphone mode. It is a small
browser state machine gated by the real Captain boot sequence:

```text
system stack ready
  -> Root page authenticated
  -> Captain SSE stream open
  -> push-to-talk arms
  -> physical press captures pointer and begins recognition
  -> physical release requests recognizer stop
  -> recognizer onend flushes final transcript
  -> exactly one existing /turn submission
```

The microphone begins every page load disarmed. It does not persist an armed
state across reload, authentication loss, or stream reconnection. This avoids
stale recognizers, permission churn, accidental room capture, and ambiguity
about whether a restarted Captain is actually listening.

## Physical protocol

- **⏳** means the authenticated Captain stream is not ready.
- **🎙** means hold-to-talk is armed.
- Press captures the pointer, unlocks Captain audio, interrupts current speech,
  and begins recognition.
- Release stops recognition and commits only after `onend`, the browser's
  authoritative transcript-flush boundary.
- A bounded 700 ms fallback covers browsers that omit `onend`; an exactly-once
  guard prevents the fallback and normal path from double-submitting.
- Pointer cancellation stops capture and submits nothing.
- Pointer movement away from the visual button no longer commits accidentally;
  pointer capture preserves the physical hold until actual release.
- Authentication or SSE loss immediately disarms and cancels the trigger. A
  new open stream rearms it without page reload.

## Boot topology learned

The static console is served by Caddy from `console/`. Port 4792 is the Root
Console API, not a static asset server. Port 4778 is the protected Captain API
and SSE stream. Process readiness, page authentication, stream readiness, and
microphone readiness are distinct states and must not be collapsed.

## Verification

- JavaScript syntax passed.
- 54 Live Captain tests passed.
- 29 Root Console tests passed, including five new trigger-protocol guards.
- Desktop and phone projections inspected with the trigger in boot-wait state.
- Live Co-Captain stack reports READY.
- Autonomous Live Captain loop remains PAUSED with continuity intact.

## Remaining acceptance gate

Only a human browser with microphone permission can prove the final physical
loop: hold, speak, release, observe one transcript submission, hear the Captain,
then press again during speech to verify barge-in. Do not mark the speech loop
accepted until the Admiral performs that test and records `✓ heard`.
