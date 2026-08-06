# Semantic Text Metamorphosis — Wired Into the Real Captain Loop

Date: 2026-08-03
Follow-up to: `2026-08-03_semantic-text-metamorphosis-shipped.md` (the
component itself, demo-button only, "not yet exercised through the real
authenticated backend").

## What changed

The capability was live but dormant: `console/index.html` had it, but
nothing connected it to the actual Captain conversation, and the Captain's
own prompt (`tools/live-captain/prompts/captain-kernel.md`) never told it
the capability existed. A killer capability nobody could trigger.

Closed the loop, live, no sandbox:

- `console/assets/js/root-console.js` (`item/completed` / `agentMessage`
  handler): added `runMetamorphosisTrigger(bodyEl)`, which scans every real
  Captain message for the tag `⟦metamorphose: phrases="a, b, c" =>
  "result"⟧`, strips it from the displayed text, and calls
  `window.liveCaptainMetamorphosis.perform()` with the parsed phrases and
  result text against the real rendered message row.
- `console/index.html`: exposed the existing `SemanticMetamorphosis`
  instance as `window.liveCaptainMetamorphosis` so the SSE handler (defined
  earlier in load order, invoked later on a real event) can reach it.
- `tools/live-captain/prompts/captain-kernel.md`: documented the capability
  and the exact trigger syntax so the Captain itself can choose to invoke
  it in real conversation. Kernel is reloaded fresh every turn — no service
  restart needed for this to take effect.
- `console/assets/js/root-console.js` (`addRow`): also ported the
  Document Viewer's per-entity identicon (`console/documents.html`) as a
  small always-on "living glyph" beside every Captain row's `captain`
  label — grounded ambient visual richness that doesn't depend on the
  Captain choosing to invoke anything.

## Verification (real, not narrated)

No Live Captain session password available this session (same limitation
as the prior log), so verified the real, unmodified, live file
(`console/index.html`, same file `cameronlampley.com/root` serves) with a
headless-Chromium script (`puppeteer-core` + `/snap/bin/chromium`,
installed to a scratch dir, not part of the app) that:

1. Loaded the actual live `console/index.html` and confirmed
   `window.liveCaptainMetamorphosis` is populated.
2. Called the real `addRow()` and confirmed the identicon glyph renders.
3. Fed `handleCodexEvent()` a synthetic `item/completed` event carrying
   message text with the trigger tag, exactly shaped like what the real
   backend sends — confirmed: tag stripped from display, source phrases
   still present, `perform()` invoked with the correct parsed phrases and
   result text, and a real `ExecutionResult` came back (`cancelled: false`,
   correct `sourcePhrases`/`resultText`, landed DOM text confirmed
   containing "testable recursive hypothesis ◆").

`node --check` clean on both touched JS files.

## Completion state

**live** — `console/assets/js/root-console.js`, `console/index.html`, and
`tools/live-captain/prompts/captain-kernel.md` are the same files
`cameronlampley.com/root` serves; no separate deploy step. End-to-end
DOM/event-handling path verified via headless browser against the real
files. Not yet observed through a real authenticated Captain turn (no
session password this session) — the gap that remains is someone with
the `/root` password watching the Captain actually emit the tag in a
live reply.
