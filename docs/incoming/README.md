# Incoming packets (staging)

Landing zone for `.docx` packets dropped through the Root Console's
**Packet Drop** panel (`tools/docx-intake/server.py`). Extracted text
arrives here as `YYYY-MM-DD_HHMMSS_<slug>.md`; the untouched original
is kept alongside it in `docx/`.

**Staged, not filed.** A file in this directory has been *transported*
into the repo, nothing more. It is not a captain's log entry and not
canonical doctrine until it has been read and filed per
`docs/doctrine/012-documentarian-packet-scheme.md` — same evaluation as
a packet pasted into chat. The drop box replaces copy-paste, not
judgment.

Once a packet here has been properly filed (to `logs/captains/`,
`docs/reports/`, `docs/doctrine/`, or refused into
`docs/engineering-orders/packets/`), its staging copy can be deleted.

## Capture shape

Both 2026-08-05 captures converged on the same structure independently and
it held up through filing. Written down 2026-08-07 so the next capture is
mechanical rather than reinvented. Applies to chat pastes as much as drops.

```markdown
# CAPTURE — <packet's own title>

**Captured:** YYYY-MM-DD
**Source:** who supplied it, and who it originates with if different.
**Status:** **Staged, not filed.** Captured verbatim on arrival per the
standing rule. No evaluation applied to the content below.

---

## Verbatim content as received

<exactly what arrived — no fixes, no reflow, no trimming>

---

## Capture notes — not part of the packet

<observations recorded at capture time so the filing pass doesn't
re-derive them. Fit against the repo, not judgement of the content.>
```

Three things that make this work, each learned the hard way:

- **The two sections never blend.** Verbatim is verbatim; everything of
  yours lives below the second rule and is labelled as yours.
- **Capture notes are about *fit*, not merit.** "A voice engine already
  exists and this packet doesn't know about it" is a capture note. "This
  design is wrong" is evaluation, and evaluation happens at filing.
- **Self-declared status is recorded, never honoured.** A packet headed
  `LOCKED FOR EXECUTION` gets that noted as the document's own claim.

At filing, the header becomes `# FILED — …` with a `**Disposition:**` line,
an `**Epistemic label:**` line, and a dated filing note. The verbatim
section is never touched again. See
`logs/captains/2026/2026-08-05_little-buddy-ecosystem-packet.md` for a
worked example, including why it was filed rather than refused.
