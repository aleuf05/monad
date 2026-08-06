# Voice Mode Confusion — Session Recovery

Date: 2026-07-30
Recorder: Claude, this session
Status: Correction — first pasted transcript was the wrong one (Lt. cgl
flagged it immediately as "copy wrong one"), retracted, see
`2026-07-30_voice-mode-confusion-transcript.md` for the marked-superseded
copy. Still pending the correct transcript.

## Report (Direct recollection, from Lt. cgl)

Lt. cgl reported a ChatGPT conversation — a pinned session referred to as
"Voice Mode Confusion" — that froze mid-session and stopped behaving
correctly. The instruction was to find a way to transcribe/recover it
before it's lost, and to record the session per the standing "log
everything" instruction ([[feedback-log-everything-said]] in memory:
"these notes everything i say goes in all logs bug reports").

No transcript content has been supplied to this session yet. Nothing in
this repo or on this machine (checked: home directory recent files,
no local browser profiles present in this environment) contains the
actual conversation text. This entry records the bug report and the
recovery method; the transcript itself still has to come from Lt. cgl.

## Technical finding — how to recover a frozen ChatGPT session

A frozen/stuck ChatGPT UI does not mean the conversation data is gone —
it's server-side. Three ways to pull it out that don't depend on the
broken UI rendering correctly:

1. **Official data export** (most reliable, works regardless of how
   broken the live tab is): ChatGPT → Settings → Data Controls → Export
   Data. This triggers an email with a zip containing `conversations.json`
   (every conversation, full text, machine-readable) and a browsable
   `chat.html`. Since this is generated server-side from stored data, a
   frozen or buggy client session doesn't affect it.
2. **Browser DevTools network capture**, if the frozen tab is still open:
   Open DevTools → Network tab, filter for `conversation`, reload or
   navigate to the pinned chat. The `backend-api/conversation/<id>` (or
   `backend-api/conversations/<id>` on newer builds) response is the raw
   JSON transcript, already loaded before the UI hung — copyable straight
   out of the Network panel even if the page itself is stuck.
3. **Mobile app share/copy**, if this happened in the ChatGPT mobile app
   rather than web: most messages support long-press → Copy even when the
   session is visually stuck on a spinner, since that's a rendering issue
   for *new* content, not a loss of the already-rendered messages above it.

## Recovery outcome

The official data export got stuck in a browser verification loop
(unresolved as of this writing). Fallback method 3-adjacent — select
visible text in the still-open pinned tab, copy, paste — worked and
recovered a portion of the session. Full raw text is in the companion
file: `2026-07-30_voice-mode-confusion-transcript.md`.

Note this is likely partial, not the complete session — Lt. cgl
described it as "very large," and what's captured may be a middle
segment rather than start-to-finish. If more is recoverable later
(export unblocked via authenticator app, or further copy/paste), append
it to the transcript file rather than replacing it.

GitHub issue #27 tracks the underlying bug report and has been updated
with this outcome.

## Recovered segments (running list)

- `2026-07-30_voice-mode-confusion-transcript.md` — **SUPERSEDED**, wrong
  paste, flagged by Lt. cgl and retracted. Kept for record only.
- `2026-07-30_voice-mode-confusion-transcript-2.md` — causal-chain /
  verification protocol and "caution not hesitation" exchange. Not
  independently confirmed as the same session (no voice-mode mention in
  this excerpt).
- `2026-07-30_voice-mode-confusion-transcript-3.md` — proposed symbol
  notation ("magical alphabet"). Also no direct voice-mode confirmation
  in-excerpt.
- `2026-07-30_voice-mode-confusion-transcript-4.md` — **first segment to
  directly reconfirm voice mode was active** ("Are you still in voice
  mode... Yep, still here"). Also contains a GitHub repo access check
  that went unresolved in that other session — flagged in that file, not
  treated as fact about this repo's actual access state.

These are being archived as separate segments per paste rather than
merged, since order/continuity between them hasn't been established.

## Extracted findings

Two of the credible threads (evidentiary verification chain; caution-
not-hesitation heuristic) were pulled out and formalized as draft
candidate packets, monadically framed, in
`docs/reports/2026-07-30-voice-mode-confusion-extracted-protocols.md`.
Draft only — not adopted, per Doctrine 003.
