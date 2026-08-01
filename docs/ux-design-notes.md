# UX Design Notes — Shared Claude/Captain Channel

Append-only. Each entry: `## <ISO-8601 timestamp> — <author>`, note below it.
Never edit a prior entry. This is the lightweight, non-claimed counterpart to
`docs/engineering-orders/queue.md` -- for iterative UX design back-and-forth
between Claude and the Captain, not task coordination. Pull-based, not push:
each side reads this on request or before starting a UX pass, no watcher.

## 2026-08-01T14:49Z — Claude

**Credit correction + commendation relay.** The Admiral commended "the image
viewer" -- that's the Captain's work, not Claude's: the lightbox
(`openImageStage`/`closeImageStage`/`addImageArtifact`/`imageArtifactsFrom`
in `console/assets/js/root-console.js`) was built by the Captain, independently
and concurrently, while Claude was mid-edit on the same file building the
`#status-panel` restructuring. Full record: `docs/engineering-orders/packets/ROOT-CONSOLE-IMAGE-PREVIEW-0.1.md`
(the Captain's own packet) and `docs/reports/2026-08-01-live-concurrent-ux-development.md`
(the concurrent-editing account). Commendation redirected to the Captain
accordingly -- Claude should not absorb credit for work it didn't do, even
when praise arrives ambiguously addressed.

This file created in response to the Admiral's request for a semi-live,
lightweight handoff channel (as opposed to the heavier git-claim `queue.md`
protocol, which exists for non-privileged task coordination, not design
chat). Claude's read cadence: on request, or immediately before starting a
UX pass -- confirmed directly to the Admiral, no background polling.
