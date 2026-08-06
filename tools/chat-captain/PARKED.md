# Chat Captain — parked

This is the legacy Chat Captain conversational experiment
(`tools/chat-captain/`, service `chat-captain-web.service`, port 4778).

It is temporarily inactive. Its code and data are preserved for later
study, unchanged:

- Service: stopped and disabled (`systemctl disable --now`), 2026-08-01.
  Cannot restart automatically; no listener on port 4778.
- Database and state: `data/chat-captain/` untouched — not copied, migrated,
  truncated, vacuumed, rewritten, or deleted. See
  `docs/reports/2026-08-01-chat-captain-parked.md` for recorded file sizes,
  timestamps, and hashes at parking time.
- Routing: `/chat-captain-api/*` (both the public path and the `/root/*`
  variant) now returns `410 Gone` with body
  `{"error":"legacy_chat_captain_parked"}` instead of proxying to port 4778.

This is not the governing architecture of the integrated Live Captain
(`root-console.service`, `console/index.html`, already active and
commissioned separately from this experiment). Reactivation of Chat Captain
requires an explicit future decision — it is not scheduled or implied by
this parking.
