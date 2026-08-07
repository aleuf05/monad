# One-Captain High-Level UX Test — Live Trace

**Intent supplied:** “Improve Living Captain UX. Figure out.”  
**Constraint:** Plan and do; observe and tweak the process.  
**Status:** Verified complete

## Explorer observation

The initial rendered page proved the machinery was present but the experience
hierarchy was inverted. Utility links, connection text, station pills, six raw
telemetry cells, and four course cards appeared before the Captain interaction.
The lower majority of the screen was empty terminal canvas. The system sounded
like a Captain in conversation but looked like a service dashboard waiting for
an operator.

## Architect decision

Do not add another feature panel. Recompose existing truth around one persistent
Captain Presence Deck. Move raw machinery down in attention, keep it available,
and make identity/state/course/command the stable bridge atmosphere across all
postures.

## Chief build shape

1. persistent presence object driven by real UI/service events;
2. compact course and posture navigation;
3. dominant conversation stage;
4. telemetry visible by posture or explicit reveal;
5. keyboard command palette for low-friction movement;
6. desktop and phone render challenge followed by one required tweak.

## Tech Lead evidence

The Captain implemented one coherent Presence Deck in the existing live Root
Console:

- persistent animated identity object with real states for connecting, ready,
  thinking, researching, speaking, and fault;
- current posture and bearing in the identity deck;
- repaired desktop course geometry (`minmax(2fr,3fr)` was invalid CSS and had
  silently collapsed the intended grid into a vertical stack);
- raw telemetry hidden outside Systems unless explicitly revealed;
- conversation stage centered with the command surface at the natural bottom;
- universal `Ctrl/Cmd+K` Helm palette that switches stations or routes a
  command into Bridge/Concept Room without creating a new conversation path;
- responsive compact identity and horizontally navigable course on phone;
- quiet first-watch invitation instead of an unexplained empty canvas.

No backend, model, authentication, station, voice, or documentary source was
duplicated.

## Challenger and verification

### Render challenge

The first post-build desktop render showed the desired hierarchy: Captain
identity first, compact course second, conversation dominant, command at the
bottom. It also exposed an overly empty first-watch canvas. The Captain added
a quiet centered `CAPTAIN ON WATCH` invitation that disappears after genuine
dialogue.

The first phone render preserved function but wrapped action controls above the
identity. Compact icon controls repaired the hierarchy. A second phone render
then exposed overlapping dynamic glyphs and clipped full identity text. The
Captain separated visual icons from dynamic button labels and deliberately
used the compact phone identity `CAPTAIN` while retaining `LIVING CAPTAIN` on
desktop.

### Verification evidence

- `node --check` passed for both Root Console browser scripts.
- 77 Live Captain tests passed.
- 24 Root Console tests passed.
- Authenticated `https://cameronlampley.com/root/` returned 200 with the new
  Presence Deck and Helm markup.
- The live Root Console JavaScript asset returned 200 with presence and Helm
  behavior.
- `live-captain-bootstrap.service` and `root-console.service` remained active.

## Process study

One Captain successfully transformed a five-word strategic hint into a large
live UX result by changing postures rather than multiplying agents:

```text
Explorer observes rendered hierarchy
  -> Architect identifies one systemic defect
  -> Chief freezes a coherent build shape
  -> Tech Lead integrates in the real target
  -> Challenger inspects desktop and phone
  -> Verifier repairs, retests, and records
```

The important process tweak is **mandatory projection review**. Source review
and automated tests could not reveal the invalid visual hierarchy, course-grid
collapse, empty-canvas feeling, phone wrap, or icon collision. For interface
work, each major posture must inspect the rendered projection, and Challenger
must receive a fixed allowance for evidence-driven refinement before handoff.

The test supports the emerging command theory: specialized behavior required
six postures but only one persistent Captain. No coordination topology was
needed because continuity, design intent, implementation knowledge, and
verification evidence remained in one command relationship.

**Final result:** PASS.
