# Live Phone Push-to-Talk Stress Test — Version 1

**Operators:** Admiral on phone; Co-Captain monitoring the vessel  
**Target:** Authenticated Monad Root Bridge  
**Safety state:** Autonomous Live Captain loop remains paused  
**Purpose:** Prove and tune the physical phone trigger through a complete spoken turn

## Command card

```text
BOOT → ARM → TAP FAULT → SHORT TURN → LONG TURN → BARGE-IN
     → RECONNECT → BURST → ACCEPT / REPAIR
```

## Before the signal

Co-Captain confirms:

- `live-captain-stack status` returns READY;
- Root Console and Captain bootstrap are active;
- pause state remains ON;
- a clean journal timestamp is marked;
- phone loads `/root/` through the real public route.

Admiral reports only what is visible or audible. Co-Captain correlates it with
`BRIDGE_SIGNAL` phases and service events.

## Test 1 — Boot and arm

**Admiral:** Reload the phone page. Do not touch the microphone yet.

**Expected:** Trigger begins as `⏳`, authentication and Captain connection
complete, then it becomes `🎙` without another reload.

**Pass evidence:** server records `armed`; phone shows the enabled trigger;
no recognition begins automatically.

## Test 2 — Cancellation boundary

**Admiral:** Press the trigger, then cancel the gesture if the phone permits
(system gesture, pointer cancellation, or leaving the page) without speaking.

**Expected:** `press → recognition-start → cancel`; no `commit`; no Admiral
message appears.

**Pass evidence:** zero `/turn` submission.

## Test 3 — Short clean turn

**Admiral:** Hold and say: **“Captain, report bridge status.”** Release once.

**Expected:** `press → recognition-start → release → commit`; exactly one
Admiral message; one Captain response; Captain voice plays once.

**Pass evidence:** transcript is materially correct, one turn only, audible
reply, no browser or service fault.

## Test 4 — Long natural turn

**Admiral:** Hold for 8–15 seconds and give a natural multi-clause request.

**Expected:** visible interim transcription while held; release preserves the
complete utterance; exactly one commit.

**Pass evidence:** no prefix duplication, truncated tail, premature commit, or
second submission. Record hold-to-commit latency from telemetry.

## Test 5 — Barge-in

**Admiral:** During Captain speech, press and say: **“Captain, hold.”** Release.

**Expected:** current Captain audio stops immediately; recognition begins; the
new turn commits once; only the new response speaks afterward.

**Pass evidence:** interruption is perceptibly immediate and no abandoned audio
resumes later.

## Test 6 — Reconnect recovery

**Admiral:** Background the browser for 10 seconds, return, and observe the
trigger. If practical, briefly change network path before returning.

**Expected:** connection loss produces `disarmed`; trigger shows `⏳`; SSE
recovery produces a new `armed`; no reload and no phantom turn.

**Pass evidence:** one clean short turn succeeds after recovery.

## Test 7 — Controlled burst

**Admiral:** Perform five short turns, waiting for each Captain response before
the next. On the fifth response, barge in once.

**Expected:** five ordinary commits plus one interruption commit; no duplicate,
lost, reordered, or merged turns; no stuck listening/thinking/speaking state.

**Pass evidence:** client count equals server commit count equals displayed
Admiral-turn count.

## Failure notation

Admiral says the smallest matching phrase:

- **“Never armed”** — remained `⏳`.
- **“No listening”** — pressed but no visible recognition.
- **“Heard wrong”** — transcript materially wrong.
- **“Sent early”** — committed before release.
- **“Sent twice”** — one release created multiple turns.
- **“Tail lost”** — final words missing.
- **“No voice”** — response visible but inaudible.
- **“Would not interrupt”** — Captain audio continued through barge-in.
- **“Stuck”** — UI phase did not recover.

Co-Captain captures timestamp, observed signal chain, expected chain, first
divergence, repair, and immediate retest. Later symptoms do not replace the
first divergence as the fault location.

## Acceptance gate

The protocol passes only when Tests 1, 3, 4, 5, 6, and 7 pass in the real phone
browser. Test 2 may be marked **not supported by browser gesture semantics** but
must never produce a phantom commit.

After the Admiral confirms the loop was understood and heard, record `✓ heard`
in the Root Bridge speech-acceptance control. The autonomous loop is resumed
only on explicit Admiral order after this test watch.
