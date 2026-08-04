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
