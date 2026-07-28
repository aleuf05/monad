# INTENTFORGE — Core Concept Packet, Version 1

**Status:** Foundational concept document. Filed verbatim for record per
Doctrine 003's capture convention — a draft capture, not a canon
promotion. No code, service, or tool exists for IntentForge yet; this
document alone does not make any of it operationally real (see its own
Section 1 standard, and `docs/research/MONAD_REALITY_PROGRAM_DRAFT_2026-07-28.md`
Section I, which this packet should be held to).

**Source:** delivered in full to this session, 2026-07-28.

---

## 1. Product Definition

IntentForge is an AI-assisted CAD system that transforms explicit physical
design intent into editable, manufacturable 3D geometry.

The system does not primarily generate visual form. It generates geometry
as the consequence of functional requirements, physical interfaces,
dimensional constraints, allowable freedoms, manufacturing conditions,
material assumptions, expected use, prohibited conditions, and observed
results from real prototypes.

The intended output is not merely an image or mesh. It is a functional
design artifact that can be inspected, dimensioned, revised, exported,
manufactured, physically tested, and improved from evidence.

The simplest success condition is: *"A person describes a needed part,
receives valid geometry, prints or manufactures it, installs it, and uses
it successfully."*

## 2. Foundational Principle

*"When design intent is encoded clearly enough, useful geometry can emerge
from the relationships contained within that intent."*

The human supplies purpose, judgment, measurements, constraints, and
acceptance criteria. The system translates those elements into a
structured design model and proposes geometry that satisfies them.
Reality determines whether the proposed geometry succeeds.

The complete loop: intent -> constraints -> relationships -> geometry ->
object -> evidence -> revision. IntentForge must preserve this loop
across every design and revision.

## 3. Public Product Promise

*"Describe the part you need by explaining what it must accomplish, what
it must fit, and how it will be made. IntentForge produces geometry you
can inspect, modify, export, and manufacture."*

The system should be understandable without requiring knowledge of its
internal architecture or originating philosophy. Its value must be
demonstrated through useful physical results.

## 4. Problem Statement

Current AI-based 3D generation commonly emphasizes visual resemblance,
surface appearance, or entertainment assets. Functional CAD requires a
different model — a useful mechanical part depends on exact dimensions,
mating relationships, tolerances, clearances, fastener geometry, material
thickness, manufacturing limitations, feature dependencies, assembly
sequence, functional purpose, and revision history. A visually convincing
mesh may still be dimensionally meaningless, uneditable, unprintable, or
mechanically useless. IntentForge addresses this gap by treating design
intent, rather than appearance, as the primary input.

## 5. Core Design Object — the Design Intent Contract

Every design must be represented by a structured Design Intent Contract
recording what the geometry is expected to accomplish and which
conditions govern its form:

- **5.1 Purpose** — what physical problem must the part solve.
- **5.2 Interfaces** — objects, surfaces, holes, fasteners, components, or
  human actions that must interact with the part.
- **5.3 Sacred Constraints** — dimensions/relationships that must not
  change during generation or revision.
- **5.4 Flexible Variables** — properties the system may select or
  optimize.
- **5.5 Keep-Out Regions** — where geometry may not exist.
- **5.6 Manufacturing Conditions** — how the object will be produced
  (FDM, resin, CNC, laser cutting, sheet metal, molding), plus additive-
  specific conditions (build volume, material, nozzle diameter, layer
  height, minimum wall thickness, allowable overhang, support preference,
  print orientation).
- **5.7 Use Conditions** — forces, motion, temperature, vibration,
  environment, frequency of use; must distinguish approximate user
  description from verified engineering requirement.
- **5.8 Failure Conditions** — outcomes that are unacceptable.
- **5.9 Acceptance Criteria** — how the user will determine the design
  worked.

## 6. Generated Output

A complete design package, not a single opaque model:

- **6.1 Editable Parametric Geometry** — meaningful dimensions, features,
  dependencies preserved wherever practical.
- **6.2 Manufacturing Output** — STEP, STL, 3MF, native/script-based
  parametric source, dimensioned drawing, manufacturing notes.
- **6.3 Intent Trace** — each important feature linked to its reason for
  existing (mounting hole -> fastener interface; rib -> stiffness
  requirement; opening -> airflow requirement; etc.).
- **6.4 Validation Report** — which checks were actually performed
  (dimensionally checked / interference checked / printability
  heuristically checked / simulated / physically tested / unverified
  proposal).
- **6.5 Assumptions and Warnings** — missing measurements, ambiguous
  requirements, contradictory constraints, and unverified engineering
  assumptions must remain visible. The system must not conceal
  uncertainty behind polished geometry.

## 7. Revision Model

The system must preserve design intent across revisions. Given a practical
observation ("the bolt head collides with this wall," "the clip is too
stiff," "keep every feature except this mounting face"), it should:
identify which contract terms changed; preserve unaffected constraints;
regenerate only what must change; explain the modification; produce a new
version; retain the previous design and its evidence. Revision history
must include both geometric changes and changes in understanding.

## 8. Initial Product Scope

Version 1 should not attempt unrestricted general-purpose mechanical
design. Initial product class: *"Printable adapters, brackets, mounts,
spacers, simple fixtures, and small enclosures."* Chosen because these
parts solve common practical problems, are understandable to
non-specialists, can be defined through measurable interfaces, are often
suitable for additive manufacturing, allow rapid physical testing, and
create a clear path from intent to evidence.

## 9. Initial User Workflow

1. Choose a part category.
2. Describe the physical need in ordinary language.
3. Identify the objects being connected, held, protected, adapted, or
   enclosed.
4. Enter or confirm critical measurements.
5. Define sacred dimensions and keep-out regions.
6. Choose manufacturing process and material assumptions.
7. Describe expected use and unacceptable failures.
8. Review the generated Design Intent Contract.
9. Generate a constrained 3D proposal.
10. Inspect dimensions, interfaces, and warnings.
11. Modify intent or geometry.
12. Export the design package.
13. Manufacture and test the part.
14. Report evidence from the physical result.
15. Generate a revised version when necessary.

The user must remain able to inspect and correct the system's
interpretation before manufacturing.

## 10. Signature Demonstration

First public demonstration: an easily understood incompatibility between
two physical objects (e.g. mounting a small device to an existing
surface), with the user providing device dimensions, mounting-hole
locations, target-surface geometry, fastener type, maximum envelope,
keep-out zones, material/printer assumptions, and desired print
orientation. Succeeds when the resulting part is printed, installed, and
shown performing its intended function.

## 11. Safety and Engineering Boundaries

IntentForge must clearly distinguish convenience-grade design assistance
from professional engineering certification. May be useful for ordinary,
low-risk parts. Must not imply verified safety for life-critical parts,
medical devices, automotive safety systems, pressure vessels, structural
building components, lifting equipment, high-voltage systems, protective
equipment, load-bearing human-support systems, or regulated/safety-
certified applications. For such uses, qualified engineering review,
appropriate analysis, testing, standards compliance, and legal
accountability remain necessary. A generated shape is not proof of
structural adequacy. A simulation is not physical validation. A
successful single print is not universal certification.

## 12. Truthfulness Requirements

Must never blur: proposed geometry / constraint satisfaction / heuristic
manufacturability / simulation / physical testing / repeated validation /
certified engineering. Suggested validation states: (1) Intent captured,
(2) Geometry proposed, (3) Constraints checked, (4) Manufacturing review
completed, (5) Simulation completed, (6) Prototype produced, (7)
Prototype tested, (8) Revised from evidence, (9) Validated for stated
use, (10) Externally reviewed. These states describe evidence — they do
not function as promotional labels.

## 13. System Responsibilities

Translating natural-language intent into structured requirements;
detecting missing/contradictory information; requesting only necessary
clarification; representing interfaces and constraints; generating
parametric geometry; maintaining feature-to-intent traceability;
preserving revision history; checking basic dimensional consistency;
detecting obvious interference; estimating manufacturability; exposing
assumptions and uncertainty; comparing design alternatives; incorporating
prototype feedback; exporting editable and printable formats; producing a
human-readable design report.

## 14. Human Responsibilities

Defining the actual physical need; supplying accurate measurements;
identifying critical constraints; reviewing the system's interpretation;
selecting appropriate materials and manufacturing methods; inspecting
generated geometry; judging acceptable risk; physically testing the
result; obtaining qualified review where safety demands it; authorizing
manufacturing and use. IntentForge augments design judgment. It does not
abolish it.

## 15. Product Character

Should feel: practical, technically serious, visually clear, inspectable,
collaborative, calm, editable, honest about uncertainty, capable of
producing delightful results without becoming theatrical. Should not feel
like: a novelty image generator, an opaque one-click magic box, a chatbot
pretending to be an engineer, a replacement for all CAD expertise, or an
unlimited autonomous manufacturing authority. May feel magical in use, but
its output must remain accountable.

## 16. Core Distinction

Traditional text-to-3D: *"description -> appearance."* IntentForge:
*"purpose -> constraints -> relationships -> functional geometry."* The
central technical and conceptual challenge is preserving the meaning of
those relationships throughout generation, editing, export, fabrication,
testing, and revision.

## 17. Governing Maxims

*"Encode the intent. Discover the form. Test the object."*
*"Every important feature should have a reason."*
*"Geometry is a proposal until reality tests it."*
*"Preserve what must remain fixed. Generate only what is free to change."*
*"The human supplies purpose and judgment. The system discovers candidate
form. Reality decides whether it works."*

## 18. Version 1 Completion Condition

Operationally real when a user can: describe a simple adapter, bracket,
mount, spacer, or enclosure; provide its important measurements and
manufacturing assumptions; review a structured statement of design
intent; receive editable 3D geometry; export a printable model;
manufacture the object; install or use it; report a concrete result;
revise the design without losing its original intent.

Decisive proof: *"The generated object performs the purpose for which it
was requested."*

---

## Filing notes (not part of the source packet)

**Nearest existing evidence in this repo:** `tools/libfive/` / the "Shape
Foundry" toy (`web/toys/libfive/`, `docs/engineering-orders/packets/
LIBFIVE-HEADLESS-1.0.md`, `LIBFIVE-CONSOLE-1.0.md`) is a real, small,
already-operational precedent — a sandboxed libfive/Guile pipeline that
generates bounded named primitives (sphere, box, torus) or raw source,
with STL output and provenance recorded in
`web/assets/libfive/manifest.json`. It is nowhere near IntentForge's
scope (no Design Intent Contract, no interfaces/keep-out/manufacturing-
condition modeling, no STEP export, no revision loop, no intent trace) —
named here only because it's the one piece of this repo's existing
machinery that sits on the same axis (constraint-bounded generative
geometry with recorded provenance), not because it should be assumed as
IntentForge's foundation.

**Resolved 2026-07-28 (Lt. cgl):** IntentForge is not core Monad
tech — it is not part of Project Monad's fleet/naval system and not
governed by Monad's own architecture doctrine. It is authorized to live
in this same repository, filed in the doc archive alongside other
material, purely as a matter of convenience. This does **not** place it
under `web/`-is-production/cameronlampley.com deployment by default —
that policy governs the Monad site specifically; if IntentForge ever
reaches build stage, its hosting/deploy model is a separate decision, not
inherited automatically from Monad's just because the doc lives in the
same repo.

**Status per the Reality Program's own standard:** entirely Doctrine/
Inquiry tier right now — a concept document, zero machinery. Recording it
does not make any capability described above operationally real.
