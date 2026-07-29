# Packet: CORE-MISSION-LIVE-REFLECTION-0.1

1. **Originating intent** — On 2026-07-29 the Admiral ordered a sixth special
   homepage destination where the redefined Core Mission could be experienced
   unfolding live.

2. **Verified starting state** — The homepage had five category cards and no
   visible place for project purpose. The restorative mission existed as an
   uncommitted, non-canonical research draft only.

3. **Objective / problem** — Add a visually distinct, click-reachable Core
   Mission reflection that presents the proposed restorative purpose honestly.

4. **Scope and exclusions** — Add one homepage card and one static reflection
   page linking to the full draft. Do not promote the proposal to canon, claim
   scientific validation, alter existing category destinations, or change
   runtime services.

5. **Constraints / authority** — Direct Admiral authorization for live public
   reflection. The page must visibly state draft status and the human promotion
   gate.

6. **Acceptance criteria** —
   - the homepage visibly contains six cards;
   - the sixth card is visually special and links directly to Core Mission;
   - the page states the proposed mission, long horizon, restorative loop,
     tangible unit of progress, boundaries, and current status;
   - draft/non-canon/non-validated status is obvious in the first viewport;
   - homepage and mission page return HTTP 200 and match committed bytes;
   - mobile rendering has no horizontal overflow.

7. **Tests / rollback** — Exact card/link counts, content markers, HTTP and
   byte checks, mobile screenshot, and navigation check. Roll back the one
   page, one card, and localized styles.

8. **Assigned actor** — Captain / Codex.

9. **Evidence / completion state** — **Verified complete, 2026-07-29 UTC.**
   Live checks found six `.cat-card` elements, with the sixth linking to
   `core-mission.html`; homepage and mission-page bytes exactly matched the
   workspace; the mission draft returned HTTP 200. A 390×844 browser check
   found zero horizontal overflow, one shared navigation element, and the
   draft status and truth boundary present on the page. Screenshots were
   inspected at `/tmp/monad-core-mission-home-mobile.png` and
   `/tmp/monad-core-mission-mobile.png`.

10. **Result** — The proposed restorative mission now has an obvious,
    visually distinct public place without being represented as adopted
    doctrine or established science.
