# Packet: HOMEPAGE-PHYSICALIST-FOOTER-0.1

1. **Originating intent** — On 2026-07-29 the Admiral ordered immediate
   removal of the homepage’s religious trust slogan as inconsistent with the
   project’s strict physicalist, evidence-bound posture.

2. **Verified starting state** — `web/index.html` displayed “IN GOD WE TRUST.
   ALL OTHERS BRING DATA.” Git traces its introduction to commit `95d49c83`,
   authored under the repository identity `Cameron Lampley
   <cgl@granite.local>` on 2026-07-12. Git alone does not establish whether
   the words were chosen by the human or an agent using that identity.

3. **Objective / problem** — Remove the religious declaration and replace it
   with concise evidence-bound language.

4. **Scope and exclusions** — Change one homepage footer line. No navigation,
   styling, doctrine, or unrelated content changes.

5. **Constraints / authority** — Direct Admiral order; `web/` is live. The
   replacement must make no metaphysical assertion and must preserve the
   existing visual structure.

6. **Acceptance criteria** —
   - the forbidden phrase is absent from the homepage;
   - the footer reads “REALITY DECIDES. CLAIMS REQUIRE EVIDENCE.”;
   - the public homepage returns HTTP 200 and matches the committed file.

7. **Tests / rollback** — Exact text search, live HTTP/content check, and byte
   comparison. Roll back the single footer line if directed.

8. **Assigned actor** — Captain / Codex.

9. **Evidence / completion state** — **Verified complete.**
   - Exact live search found “REALITY DECIDES. CLAIMS REQUIRE EVIDENCE.”
   - Exact live search found no occurrence of “IN GOD WE TRUST.”
   - `https://cameronlampley.com/` returned HTTP 200.
   - Live homepage bytes matched `web/index.html`.
