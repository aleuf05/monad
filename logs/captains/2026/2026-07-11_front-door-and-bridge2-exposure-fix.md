# Front Door Rework & Bridge-2 Exposure Fix Watch Log

Date: 2026-07-11
Operator: Commander Claude, Engineering Watch
Directed by: Admiral C — "make the front door links to all toys."
Objective: replace the site root's redirect-into-Bridge-Station behavior with a homepage linking every deployed public toy, and — surfaced during this work — fix an accidental public exposure of a LAN-only toy.

## Incident: `toys/bridge-2/` briefly public

While deploying `toys/reaction-diffusion-painter/` (an unrelated, planned addition) earlier in this session, a routine `rsync -av --delete web/ /var/www/monad/` also copied `toys/bridge-2/` to production, because it had been living inside `web/toys/bridge-2/` so the LAN-only python server (port 8090, which serves the whole `web/` directory) could find it — but nothing had ever excluded it from the *public* deploy path, which rsyncs that same directory. Caught immediately (operator asked "is site live," prompting a check) — confirmed the public site itself was fully healthy, with `toys/bridge-2/` additionally, wrongly, returning `200`. Not a data exposure (the page would just show "Reconnecting…" forever for a public visitor, since `fleetcore-serve` isn't publicly reachable) but a real information disclosure (the toy's existence, source, and expected backend port become publicly visible) and a process failure worth fixing properly, not just patching once.

Root cause: `web/` was being used for two different purposes — "the public deploy bundle" and "LAN-only extras," with no structural separation enforcing which was which. Any future `rsync web/ /var/www/monad/` would have re-exposed it.

**Fix:** relocated `toys/bridge-2/` (and its `../shared/fleet-state.js` dependency) out of `web/` entirely, into a new top-level `web-lan/` directory that the public deploy path never touches. Restarted the port-8090 server to serve `web-lan/` instead of `web/`. Verified: `https://cameronlampley.com/monad/toys/bridge-2/` now `404`s (removed from production by the same `--delete` rsync that previously added it, once the source directory no longer contained it), while `http://192.168.0.100:8090/toys/bridge-2/` still works. This is a structural fix, not a one-time cleanup — nothing in `web-lan/` can ever be swept into a public deploy by an ordinary `rsync web/ /var/www/monad/`, because it isn't part of `web/` at all.

## Front Door

Previously `web/index.html` was a redirect (instant meta-refresh + JS fallback) straight into `toys/bridge/`, with the actual homepage content preserved at `web/command-deck.html`. Reversed: `web/index.html` is the homepage again — mission/doctrine/fleet roster/Ship's Log content plus an "Interactive Artifact" section linking every deployed public toy. `web/command-deck.html` is kept as an identical mirror (same content, distinct `<title>`) rather than removed, so the URL anyone bookmarked during the redirect era still works.

Added a direct launch card for **Periscope Station**, which had never had a standalone link on the homepage before (only reachable via Bridge Station's embedded panel) — now genuinely "links to all toys," not just most of them. Final public toy roster: Radio Console, FleetCore Live, Bridge Station, Fleet Motion Mk2, Periscope Station, Reaction-Diffusion Painter.

`toys/reaction-diffusion-painter/` was also deployed publicly for the first time in this same pass (fully self-contained, zero backend/data dependency, no privacy concern — unlike Watchbook, which the operator explicitly chose to keep undeployed entirely when asked).

## Verification

Playwright against a local server: confirmed the root page no longer redirects (stays on `/`, title "Monad"), confirmed all 6 toy launch links are present, and fetched every linked path directly to confirm each resolves (all `200`). Post-deploy, verified the same against the live public site, plus confirmed `toys/bridge-2/` correctly returns `404` publicly while remaining reachable on the LAN via its relocated path.

## Follow-up

`docs/deployment.md` updated to describe both changes, including a new instruction that `web/index.html` and `web/command-deck.html` must be updated together (no longer redirect-plus-fallback, now two independent copies of the same content) — worth eventually replacing the duplication with one file and a redirect the other way, but not done in this pass.
