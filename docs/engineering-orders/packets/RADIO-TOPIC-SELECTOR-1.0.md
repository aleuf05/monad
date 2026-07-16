# Radio Topic Selector 1.0

1. **Originating intent** — The Lieutenant ordered Engineering to pick a Radio Console topic and start on 2026-07-16.
2. **Verified starting state** — Radio Console displays the live NPR feed as passive links. The feed supplies title, URL, and publication time but no summary text.
3. **Objective / problem** — Turn the newest real headline into a visible lead topic and allow operators to select another headline without misrepresenting feed data.
4. **Scope and exclusions** — Modify Radio Console HTML, CSS, and JavaScript in source and live trees. Do not synthesize summaries, speak real news as fleet traffic, alter the NPR fetcher, or touch services.
5. **Constraints / authority** — Public functionality must be obvious, deployed to `web/`, click-reachable through the existing homepage card, and verified at the live URL.
6. **Acceptance criteria** — Newest headline is selected by default; selected topic, source/time, and NPR link are visible; clicking another headline changes selection; selected state is obvious; embedded layout remains compact.
7. **Tests / rollback** — Run JavaScript syntax validation, source/live drift check, and live HTTP content checks. Roll back by reverting the implementation commit.
8. **Assigned actor** — Codex.
9. **Evidence and completion state** — Verified complete and recorded. `node --check toys/radio-console/app.js` passed. `python3 tools/check-toy-drift.py` reports source/live synchronization. Live HTTPS checks confirmed the `Newswire Topic`, `Lead topic`, versioned script, and selection handler at `https://cameronlampley.com/toys/radio-console/`. The current feed selected its newest Hong Kong bookseller/security headline by default.
