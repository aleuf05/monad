# IntentForge (provisional codename)

Not core Monad tech. Lives in this repo for convenience; not under
`web/`'s deploy policy. An ongoing, evolving experiment, not a bounded
sprint deliverable -- treat this README as a snapshot of where it
currently stands, not a spec.

**Absorption note (2026-07-29):** built by one occupant of the Captain
role, in a session that later discovered a separate, more established
Captain-CLI thread already running on this branch (see the addendum in
`docs/engineering-orders/CAPTAIN-CLI-ROLE-IMPLEMENTATION-0.1.md`). This
directory is intentionally self-contained (no dependency on anything
outside `intentforge/`) specifically so it can be picked up, evaluated,
or absorbed by whichever Captain identity eventually unifies, without
needing this session's conversation for context. It is not yet claimed
by, or reconciled with, that other thread's work -- if you're arriving
here as that occupant, this is a candidate work-stream to fold in via
whatever role-registry or work-queue mechanism exists by then, not
something to silently adopt as already-integrated.

## What exists right now (v0.0)

A working, tested, pure-Python solid-geometry engine (`mesh.py`) and one
part generator built on it (`bracket_generator.py`): a flat plate with
circular holes and one edge keep-out notch. `demo_fan_bracket.py` runs
the concept packet's own worked example (a 40mm-fan mounting bracket)
end to end and writes a real, watertight, dimensionally-verified binary
STL to `output/`.

Run it:

```sh
cd intentforge
python3 demo_fan_bracket.py      # generates output/fan-mount-bracket-v0.stl + a JSON report
python3 -m unittest test_bracket_generator.py -v
```

Why pure Python instead of the real libfive backend this repo already
has (`tools/libfive`): the exporter binary isn't installed on this
machine (`python3 tools/libfive/generate.py status` -> `installed:
false`) and the libfive source isn't checked out locally either, so
there was no way to write or verify real Guile/CSG script against it.
Writing that code anyway would have been an unverified claim dressed as
geometry. This engine is deliberately small enough to fully test without
any external dependency, and it already caught two real bugs during
development (a watertightness-check bug and a hole-wall winding bug that
was silently adding volume instead of removing it) that would have
shipped invisibly with a black-box backend.

`design_intent.py` holds a deliberately narrow slice of the full Design
Intent Contract from the concept packet -- only what this one generator
can actually back up with real geometry, not the full 5.1-5.9 shape.

`ValidationStatus` mirrors the packet's truthfulness states in code, not
just prose: every field defaults to `False` and the generator can only
set the ones it actually earned. Current honest state for anything this
generates: geometry proposed, constraints checked, printability
estimated (bounded by wall-thickness rule). Not simulated, not
manufactured, not physically tested, not externally reviewed, not
validated for any use.

## Growth path (not built, not promised -- just the visible next steps)

- Swap this extrusion engine for real libfive CSG once the exporter is
  actually installed (a `cmd.sh` step, not something this session can do)
  -- `design_intent.py`'s contract shape shouldn't need to change, only
  `bracket_generator.py`'s backend.
- STEP export (a real CAD kernel -- e.g. build123d/OpenCascade -- would
  need to be deliberately added; not assumed here).
- Widen `design_intent.py` from "flat plate with holes and one notch"
  toward the full contract (arbitrary interfaces, non-planar geometry,
  manufacturing-process-aware checks beyond wall thickness).
- Natural-language intake in front of the structured contract (matching
  this repo's existing Gemini-based pattern elsewhere, if/when that's
  wanted).
- The revision loop from the concept packet (report a physical problem,
  regenerate only what must change, keep prior versions) -- nothing here
  yet touches revision at all; every run is a fresh generation.
