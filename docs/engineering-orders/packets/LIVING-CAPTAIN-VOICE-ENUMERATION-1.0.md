# Living Captain Voice Enumeration 1.0

1. **Originating intent** — The Lieutenant reported Living Captain displaying “No TTS voices installed.”
2. **Verified starting state** — The shared browser-speech provider called `speechSynthesis.getVoices()` once and immediately treated an empty initial result as proof that no voices existed. Living Captain uses this provider in both source and live copies.
3. **Objective / problem** — Allow the browser time to complete asynchronous voice enumeration before Living Captain reports that no TTS voices are installed.
4. **Scope and exclusions** — Update the shared browser provider, its live mirror, and its unit test. Do not add a cloud provider, credentials, server-side speech, packages, or privileged host changes.
5. **Constraints / authority** — Preserve Browser Speech as the default, keep a genuinely voiceless browser’s visible failure, and keep `toys/` and `web/toys/` synchronized.
6. **Acceptance criteria** — A voice available immediately is selected as before; a voice populated shortly after the first empty result is selected; a browser still empty after the bounded wait retains the existing error; source/live shared modules match; the live page serves the updated logic.
7. **Tests / rollback** — Run the shared Node unit test, JavaScript syntax checks, source/live comparison, and live HTTPS marker check. Roll back the implementing commit to restore immediate enumeration.
8. **Assigned actor** — Codex.
9. **Evidence and completion state** — Verified complete and recorded. The Node test proves immediate selection, delayed voice enumeration, and the bounded zero-voice failure. Both shared JavaScript copies pass syntax checks and compare byte-for-byte. Live HTTPS serves `waitForBrowserVoices`, the 1500 ms bound, and the `voiceschanged` listener; the live Living Captain page still loads that shared module and exposes the visible Read Status control.
