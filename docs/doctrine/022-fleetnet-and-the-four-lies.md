# Doctrine 022 — FLEETNET: active ≠ routed ≠ reachable ≠ working

**Authority:** Admiral cgl, 2026-08-05 — *"sound the plumbing"*, *"sound
fleetnet 5 x 5"*, *"make canon"*.

Canon. Written after four instruments told four different lies about the
same fleet inside one hour.

---

## The four states, which are not the same state

| Question | Instrument | What it cannot tell you |
|---|---|---|
| Is the unit running? | `systemctl is-active` | whether it is installed; whether anything routes to it |
| Is there a route? | grep the Caddyfile | whether the route resolves; whether the service answers |
| Is it reachable? | `curl` a prefix | whether the path is served, or merely the prefix |
| Does it work? | `curl` a real endpoint | nothing else does |

Each is cheap. Each is plausible. **Each disagreed with the next on
2026-08-05.**

## What each one got wrong, on the day

**`is-active` said `active`.** `rich-voice` was running and completely
unrouted — `/voice-api/status` returned 404 from the internet with the
service answering 200 on loopback. A configured Gemini key, a full budget,
and no pipe.

**A Caddyfile grep said "no route" for `m3-cycle`.** The route exists. The
grep window was six lines and the block is eight. The same window mismatched
ports 4791 and 4793 and reported a route conflict that does not exist.

**A prefix probe said ten services were broken.** Nine were fine.
`/gasket-upload-api/` returns 404 while `/gasket-upload-api/api/status`
returns 200 — the route works, the service simply has no handler at `/`.
**A status code cannot distinguish "no route" from "no root handler."**

**A port scan said 4369 was ours.** It is Erlang's port mapper, listening
on `*`, belonging to something else on the host entirely.

Four instruments. Four wrong answers. All four were about to be reported.

## The rule

> **Only a request to a real endpoint from outside proves anything. Every
> cheaper check answers a different question and must be labelled with the
> question it answers.**

## Practice

1. **Probe endpoints, never prefixes.** A prefix 404 is uninformative by
   construction.
2. **Read auth codes as success.** `401` and `302` across this fleet mean
   `public-root-auth` is working. A report that flags them as faults is
   measuring the gate and calling it a leak.
3. **Check only what is unambiguous, mechanically.** `sound-the-ship.sh`
   step 5 was narrowed to exactly one question — *a listening port with
   nothing pointing at it* — because that is the only plumbing fact a script
   can establish without knowing each service's path table. It reports two:
   4369 (not ours) and 4775 (`rich-voice`, the real gap).
4. **Widen a grep window before trusting a negative.** Two of the four lies
   were a six-line window over eight-line blocks.

## FLEETNET, as sounded 2026-08-05 10:43Z

| Service | Unit | Loopback | Public |
|---|---|---|---|
| root-console | active | 401 | 401 |
| aegis pipeline | active | 200 | 401 |
| m3-cycle | active | 404¹ | 401 |
| docx-intake | active | 404¹ | 401 |
| gasket-upload | active | 200 | 200 |
| live-captain boot | active | 401 | 401 |
| live-captain chat | active | 401 | 401 |
| public-images | active | 200 | 200 |
| **rich-voice** | active | 200 | **no route** |

¹ These do not implement `/api/status`; they answer 401 publicly, proving
route and gate both work. Different endpoint, not a broken service.

23 units installed, 19 active, 18 ports held. Front page 200, console 302.

## The standing gap

`rich-voice` — Gemini TTS, key configured, budget capped at $0.10/day and
untouched, tested router in front of it, and **no Caddy route**. One
consumer already fails silently against it:
`web/toys/character-voice-studio/app.js` calls `/voice-api/...`, and a 404
on a voice render is indistinguishable from a voice that did not play.

Adding the route is a handful of lines. It is not done because it converts
the Buddy from a free local voice to a metered paid one, and that is the
Admiral's decision, not an engineering one.

## Related

- `019-general-orders.md` — order I, of which this is the fleet-scale case
- `021-count-the-host-not-the-document.md` — the count; this is the plumbing
- `scripts/sound-the-ship.sh` — steps 3, 4 and 5
