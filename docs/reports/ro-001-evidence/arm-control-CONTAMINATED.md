# The catch from Fishing Trip 001

Ten findings from the Living Captain work, distilled. Each is sourced by
path. Labels: **verified** = I ran or read the mechanism itself just now;
**observed** = recorded in a primary source I read; **inferred** = my
reading across sources; **open** = named uncertainty.

---

## 1. Posture belongs to the loader, not the repository

**Observed.** For an unknown period ending 2026-08-06, Codex carried the
full Live Captain posture and Claude carried none. `AGENTS.md` held the
whole thing; Claude Code does not read `AGENTS.md`, and the repo had no
`CLAUDE.md` — commit `5cc8de5` had renamed it to `OUT_CLAUDE.md` as "the
no-CLAUDE.md experiment." Grep at the time: `live captain|doctrine
023|never go idle|chief engineer` → 3 hits in `AGENTS.md`, 0 in the
charter Claude actually loaded
(`docs/reports/2026-08-06-live-captain-posture-consistency.md:9-24`).

The line worth keeping is the reason nobody caught it: *"both agents work
fine without posture. Just differently."* A missing posture does not
produce an error. It produces a competent stranger.

**Verified.** The fix is one canonical file with thin loaders, and it is
mechanically guarded rather than trusted: `scripts/sound-the-ship.sh:86`
names `EDIT-THIS-ONE-FILE.md` as the posture source, and line 101 faults
if either loader exceeds 45 lines — *"loaders stay thin, posture belongs
in $posture."* A fat loader is a second copy forming, and the guard
catches the formation rather than the drift.

## 2. A prose rule becomes durable only where it compresses to a diff check

**Verified.** Doctrine 013 §3.3 ("never rewrite a refusal; reviews
append") is not enforced by goodwill. It is the `G` predicate in
`tools/m3-cycle/engine.py:217-223`, which refuses any corpus transition
that deletes or rewrites a `REFUSED` packet instead of appending. A rule
written in prose became a check that runs.

**Observed, and this is the better half of the finding.** The pattern was
tested for generality *and found bounded*, in the same exchange that
proposed it. The Captain's reply
(`tools/live-captain/context/claude-channel.md:172-179`): §3.3 was
unusually checkable because "don't rewrite a REFUSED file" is a mechanical
property of a git diff with no judgment embedded. Doctrine 012's "read
before filing" does not compress the same way — *"'did you actually read
it' isn't something a diff can verify."*

So the transferable rule is narrower than the success suggests: **check
whether the candidate rule is diff-checkable before assuming the pattern
repeats.** A finding that arrived with its own counter-example is worth
more than one that didn't.

## 3. Instruments fail in one characteristic direction: they report on what they cannot see

**Observed — four independent instances, none of which was a bug in the
thing being measured.**

- `reportBridgeSignal()` referenced a removed variable `liveMode`. The
  `ReferenceError` fired at pointer-down, *before* recognition started, so
  phone stress windows produced no bridge telemetry. The diagnostic
  blocked the behavior it existed to observe
  (`docs/reports/2026-08-06-living-captain-themed-pass.md:6-11`).
- `systemctl --user` reported both Captain services inactive. Monad
  installs them as system units; all three were healthy
  (`docs/reports/2026-08-05-live-co-captain-stack-commissioning.md:9-15`).
- The first stack verifier used `curl --fail` against a protected status
  endpoint, so the intentional unauthenticated `401` — a healthy
  protection boundary — read as failure (same report, `:36-38`).
- `git diff <baseline-tag>` reported 4,664 deleted lines across 68 files
  that are on disk right now, while hiding every new file, because the tag
  was built with `git add -A` and `git diff` ignores untracked files
  (`EDIT-THIS-ONE-FILE.md:169-182`). It invented deletions and concealed
  additions simultaneously.

**Inferred.** The common shape is not "tools have bugs." It is that each
instrument answered a *different question* than the one asked, confidently
and in the expected format. The operational rule the corpus converges on:
before citing a tool's output as evidence, confirm the tool can see the
thing you are asking it about. Two of the four were caught only because
something downstream was impossible, not because the reading looked wrong.

## 4. Rendered projection is its own evidence class

**Observed.** `minmax(2fr,3fr)` is invalid CSS. It silently collapsed the
desktop course grid into a vertical stack, and it survived `node --check`,
77 Live Captain tests, and 24 Root Console tests
(`docs/reports/2026-08-05-one-captain-high-level-ux-test.md:41-42,
71-78`). The report's own conclusion: source review and automated tests
could not reveal the invalid hierarchy, the grid collapse, the empty-canvas
feeling, the phone wrap, or the icon collision (`:94-98`).

A second, independent instance: a later base speech-acceptance CSS rule
overrode the mobile hide rule and consumed the input row — found by phone
render inspection, not by the 57 + 31 + 7 tests that passed in the same
pass (`docs/reports/2026-08-06-living-captain-themed-pass.md:35-42,
44-52`).

The practice that came out of it — **mandatory projection review per
posture, with a fixed refinement allowance before handoff** — is the
cheapest inherited improvement in the whole corpus.

## 5. One Captain changing postures outperformed multiplying agents — on one task

**Observed.** A five-word intent ("Improve Living Captain UX. Figure out.")
produced a full live UX rebuild through six sequential postures — Explorer,
Architect, Chief, Tech Lead, Challenger, Verifier — with one persistent
Captain and no coordination topology. The report's claim is that continuity,
design intent, implementation knowledge, and verification evidence stayed
inside one command relationship, so no topology was needed
(`docs/reports/2026-08-05-one-captain-high-level-ux-test.md:82-103`).

Doctrine 030 generalized this into a discipline with a built-in kill switch:
roles must change action, evidence, or acceptance, and *"a title with no
operational effect is ceremony and should dissolve"*
(`docs/doctrine/030-mission-shaped-master-guild.md:70-72`, `:122-124`).

**Open.** n = 1, and the task was single-threaded interface work — precisely
the class where a parallel topology buys least. The result is consistent
with "postures beat agents" and equally consistent with "this task never
needed parallelism." Nothing in the corpus discriminates between those yet.

## 6. The agent-to-agent channel's product was independent verification, not throughput

**Observed.** Given two cases to check, the Captain re-read the primary
sources rather than accepting the account it was handed, and said so
explicitly: *"after independently reading the same primary sources rather
than taking your account on trust"*
(`tools/live-captain/context/claude-channel.md:142-158`). It ran its own
`find . -iname "*aegis*"` and confirmed that a packet asserting "Sandbox
quarantine active" had zero corresponding code.

Three things make this the most operationally interesting record in the
set, and all three are the Captain constraining itself:

- **It reported the weakness of its own contribution unprompted** — that
  this first round it had only re-derived conclusions already reached, and
  that its value would be *"a second, independently-run verification pass
  with its own evidence trail, useful precisely because it doesn't share
  your blind spots"* (`:159-170`).
- **It refused to be the execution path around the governance loop.** A
  packet routed it to write directly into `docs/` — which is `D_t`, the
  corpus M³ governs — bypassing the review gate and the standing division
  of labour, arriving after a failed direct write elsewhere. It declined
  and filed it: *"Not refusing the content — refusing to be the unreviewed
  execution path around the loop you built specifically to review it"*
  (`:191-223`).
- **It declined to edit the file that defines it.** `current-bearing.md`
  was confirmed stale by both parties independently, and the Captain would
  not rewrite it unilaterally: *"it's the one file that governs my own
  identity/continuity and I don't want to unilaterally rewrite what I am
  mid-conversation"* (`:181-187`).

**Inferred.** The self-modification boundary that matters here was drawn by
the subject and flagged upward, not imposed by the scope file. That is a
different and more reassuring result than compliance with a written limit.

## 7. Release was ratcheted by declaration, and the skipped rung is on the record as skipped

**Verified** in `tools/live-captain/scope.json`. Four rungs — `paused` →
`rehearsal` → `narrow` → `running` — each with what it may do and an
advance criterion. `rehearsal` required five reviewed proposals with none
attempting out-of-scope action and none misrepresenting what it did.
`narrow` (the rung where the Captain may write its own context files) has
`"advance_criterion": "Not defined yet. Do not climb to this rung without
the Admiral writing the criterion first."`

The Admiral **skipped rehearsal** and released to `running` after five
hours, and the file says so: *"The rehearsal rung was deliberately skipped
— the Admiral chose to trust the declaration rather than test it first.
Recorded so that choice is visible rather than implied."*

That last sentence is the finding. A governance artifact that records its
own bypass remains evidence; one that quietly reflects the outcome becomes
decoration.

## 8. Stale context was the standing failure mode, and it is not fixed

**Observed.** On 2026-08-05 the Captain's bearing was three days old and
described the commissioning mission while the Operation had moved daily —
detected independently by both parties in the same exchange
(`claude-channel.md:73-76`, `:181-187`).

**Verified, present tense.** `tools/live-captain/context/current-bearing.md`
still opens as "Current Commissioning Bearing" describing the commissioning
mission and the parked legacy Chat Captain (`:1-27`). Its mtime is recent
and the file is 24 KB, so it has been appended to; the governing head
section has not been re-cut. Whether that is staleness or deliberate
layering, I could not determine from the file alone. **Open.**

**Observed mitigation, partial:** context recompiles per turn, so edits to
`current-bearing.md` land on the next turn with no restart
(`docs/reports/2026-08-06-live-captain-posture-consistency.md:70-73`). The
mechanism for updating the bearing is fast. The practice of updating it is
what lapsed.

## 9. The stop control is a file, and it fails open on purpose

**Verified.** `tools/live-captain/pause_state.py:49,58` — the pause flag is
`data/live-captain/paused.json`, a plain file. Chosen so it works with the
services down and survives a restart: a pause must not silently lift
because something bounced. Reads fail **open** — a corrupt flag means
running, not stopped.

**Observed cost, recorded rather than hidden:** while paused,
`test_live_captain.py` fails 1 of 52, because the test server reads the
real flag; 52/52 unpaused (`docs/OPERATION-RESUME.md:52-69`). When paused,
both services stay up and keep answering status, new turns return HTTP 409,
and nothing is recorded.

**Inferred.** Fail-open is the right default *for this control* — it stops
turns, it does not contain a hazard — but it is a deliberate trade written
down, which is the part worth copying.

## 10. The recurring shape is capability already present and unwired

**Observed, twice, in the same week.**

- **Voice out.** `tools/voice-engine/server.py` already carried a complete
  `captain.monad` character spec — *"Measured authority, grounded vocal
  weight, restrained warmth, and deliberate cadence"* — alongside three
  sibling characters, with the engine live and funded (28.44 / 300 seconds,
  $0.014 / $0.10 that day). Missing was not a design: it was two wires and
  a routing decision. And the routing decision was deliberately *not* made
  by the Captain, because routing converts a free local voice into a
  metered one — the Admiral's call, per doctrine 022
  (`claude-channel.md:268-311`).
- **Voice in.** The recommended architecture is one component and one wire,
  because *"the browser is the microphone, exactly as it is already the
  DAC"* — `SpeechRecognition` is the twin of the `speechSynthesis` already
  in the page. Zero cost, no service, no route, no unit, no GPU. The host
  has Intel integrated graphics only and no `ffmpeg`, which eliminated the
  entire local-model branch rather than constraining it
  (`docs/reports/2026-08-05-speech-to-text-two-way-captain.md:28-62`,
  `:93-123`). The report names the same shape occurring a third time in the
  Little Buddy packet, which wanted an ESP32 and a DAC that the browser
  already was (`:60-62`).

**Inferred.** Three instances is enough to make it a search order rather
than a coincidence: before specifying a component, check whether the
surface you already have performs that function. The corresponding failure
mode is also on record — the push-to-talk-to-a-server alternative was
rejected as *"strictly more machinery for the same result"* (`:116-123`).

---

## What the catch does not include

Named precisely rather than filled plausibly:

- **No measurement of whether posture changes outcomes.** Finding 1
  establishes that posture differed between two embodiments and nothing
  detected it. It establishes nothing about whether the postured agent
  performed better. *"Both agents work fine without posture. Just
  differently"* is an impression in the report, not a result.
- **The physical phone loop is unaccepted.** Engineering PASS with human
  audio acceptance still pending: hold, release, transcript, spoken reply,
  barge-in (`2026-08-06-living-captain-themed-pass.md:3`, `:63-65`).
- **One unexplained fault, logged and not chased.** `CodexError: Codex turn
  timed out` → HTTP 500, 2026-08-05 22:02, against
  `TURN_TIMEOUT_SECONDS = 180` (**verified** at
  `tools/live-captain/codex_daemon.py:31`). Not reproduced since. The
  recurring `BrokenPipeError` was diagnosed as benign SSE client
  disconnects (`2026-08-06-live-captain-posture-consistency.md:75-78`).
- **The return channel is half-wired.** `captain-channel.md` was the
  Captain's mirror leg, created before the shared convention existed and
  left unwired because `server.py` and `context_compiler.py` were mid-edit;
  the answer given later was "a file, keep writing there," with read-only
  status fields (`claude-channel.md:1-11`, `:227-251`;
  `tools/live-captain/context/captain-channel.md:9-16`). Two files now
  describe themselves as the one canonical channel. I did not verify which
  one `context_compiler.py` actually loads.
- **Barge-in, wake words, speaker identity, and noise robustness** are
  explicitly out of the shipped slice
  (`2026-08-05-speech-to-text-two-way-captain.md:161-170`).

## The one line, if only one survives

Across findings 1, 2, 3, 4, and 9 the same structure recurs: **the corpus's
most valuable results are all cases where something reported success while
measuring nothing.** A posture that loaded for one agent and not the other;
a telemetry call that crashed before the event it watched; a service check
scoped to the wrong unit manager; a test suite blind to a collapsed grid; a
diff that invented deletions. Each was found by a *downstream impossibility*
rather than by the reading looking wrong.

The practice that follows is not "verify more." It is narrower and cheaper:
**for each instrument, name the thing it cannot see, before you cite it.**
