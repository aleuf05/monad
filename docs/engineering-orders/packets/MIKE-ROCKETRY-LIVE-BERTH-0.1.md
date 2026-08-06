# MIKE-ROCKETRY-LIVE-BERTH-0.1

## 1. Originating intent

**Human ruling, 2026-07-29:** The Admiral ordered the Captain to create a
special spot at the top of the live site for Mike immediately, while the
larger rocketry-completion project is being built.

## 2. Verified starting state

`web/index.html` had no Mike or rocketry entry. The live homepage began with
the Fleet Monad banner, status strip, general lede, and category grid.
`web/toys/mike-rocketry/` did not exist. Four unrelated live-generated JSON
snapshots were already modified and were not touched.

## 3. Objective / problem

Give Mike's special project an unmistakable, click-reachable berth at the top
of the production homepage and a stable destination for the playable lab.

## 4. Scope and exclusions

Scope: one prominent homepage feature card and one initial destination page.
Excluded: the simulator itself, completed equations, GitHub publication, and
claims that the project is finished.

## 5. Constraints / authority

The Admiral explicitly authorized immediate live implementation. Repository
doctrine requires an obvious marker, click reachability, real-URL validation,
and truthful presentation of incomplete state.

## 6. Acceptance criteria

- A Mike project card appears above the homepage lede and category grid.
- The card is marked new and under active construction.
- The card links to `/toys/mike-rocketry/`.
- The destination states that the playable lab is being built, not complete.
- Both production URLs return HTTP 200 and expose the expected visible text.

## 7. Tests / rollback

Validate HTML references locally, then request the real homepage and project
URL and inspect their status and identifying text. Rollback is the removal of
the card, destination directory, and this packet in a later commit.

## 8. Assigned actor

Captain / Codex CLI.

## 9. Evidence and completion state

**Lifecycle:** verified complete → recorded.

Verified 2026-07-29:

- local linkage and marker assertions: PASS;
- `https://cameronlampley.com/`: HTTP 200, with visible `BUILDING LIVE` and
  `THE VARIABLE-EXHAUST ROCKET LAB` text;
- `https://cameronlampley.com/toys/mike-rocketry/`: HTTP 200, with visible
  project title and `BUILDING LIVE` state;
- pre-existing `web/data/*.json` modifications remained unstaged and
  untouched.
