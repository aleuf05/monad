# Microcontroller & Acceleration Architectures — Research Packet

Date: 2026-08-03

Prepared for: Admiral

Scope: a submitted research packet (`RSP-PMA-2026-08`) surveying Tang Nano
(FPGA), RP2040, and ESP32 as potential hardware acceleration/edge targets.
This is a reference record of the idea, not an implementation report --
nothing described here exists in this repository or on any live Monad
service today. Filed per `docs/engineering-orders/packets/README.md`'s own
distinction: packets are for work that changes the repo or a live service;
pure research/synthesis with no such change belongs in the report queue
instead, which is why this lives here rather than under `packets/`.

## Verified starting state

`grep -ril` across the repository for `RP2040`, `ESP32`, `Tang Nano`, `FPGA`,
`Verilog` returns no hits outside two incidental mentions in
`web/toys/mike-rocketry-notebook/` (Mike's own rocket-equations notebook,
unrelated to this packet's specific proposals). No Monad service currently
targets any of these platforms.

## Part II — platform application vectors (technically grounded)

The three platforms named are real and the proposed uses are standard,
credible practice for each:

- **Tang Nano (9K/20K) as a coprocessor** -- using a low-cost FPGA for
  fixed-function, low-latency pipeline work (pixel shifting, pattern
  matching, protocol conversion) offloaded from a host MCU is a normal,
  well-established FPGA use case. No red flags.
- **RP2040 PIO as a protocol bridge/logic analyzer** -- the PIO
  (Programmable I/O) block is exactly RP2040's standout feature for this;
  bit-banging precise or legacy serial protocols independent of the two
  Cortex-M0+ cores is a widely used, well-documented pattern.
- **ESP32 as a distributed telemetry/control node** -- dual-core plus
  integrated Wi-Fi/BLE for local sensor aggregation and lightweight
  filtering before pushing telemetry is a common, practical edge-node
  design. No red flags.

None of this is built or scoped against Monad's actual needs yet; it reads
as a legitimate but generic hardware-platform survey, not a project-specific
plan. If any of these gets pursued, it needs its own scoped packet with a
real target (what would it control or read for *this* project) before it
becomes actionable work.

## Part III — "Emoji Association Matrix"

This section maps five arbitrary emoji to engineering concepts (stag ->
low-latency routing, cucumber -> thermal management, fever face -> error/
overload states, piano -> multi-channel timing, pickaxe -> data extraction)
as a "methodology." Recording it here for completeness since it was part of
the submitted packet, but flagging it plainly: this is a mnemonic/creative
naming device, not an engineering methodology, verification technique, or
anything with technical content of its own. It shouldn't be cited later as
a design framework -- the actual technical substance for each concept
(interrupt latency, thermal budgets, watchdog thresholds, clock-phase
alignment, log parsing) is real and worth keeping; the emoji labels are
just mnemonics for it, not a source of engineering rigor.

## Addendum (2026-08-03) — Admiral's Operational Briefing, doctrine for Project PMA

A follow-up transmission proposed four operating rules for PMA, framed as
executive directives. Recorded here as **proposed doctrine for a project
that does not yet exist in Monad**, not adopted Monad doctrine (compare
`docs/doctrine/`'s actual entries, e.g. Doctrine 001, which were adopted
only after a real incident occurred in this repo). If PMA is ever actually
scoped and built, promoting some or all of these into a real doctrine file
would be reasonable; until then this is a record of the proposal, per
[[monad-transmission-posture]].

1. **Never let the radio touch the trigger** -- keep ESP32's Wi-Fi/BT stack
   off the real-time control path; perimeter/telemetry role only.
2. **Let hardware do hard labor** -- push sub-microsecond/bitstream work down
   to the Tang Nano FPGA or RP2040 PIO, not the ARM cores.
3. **Respect the piano keys and the fever face** -- strict GPIO clock/phase
   discipline, plus hardware-level (not just firmware) thermal/current trip
   protection.
4. **Document the blueprint before you burn the code** -- formalize a
   strategy-packet pipeline before ad-hoc implementation.

### Engineering commentary (offered freely, per invitation)

- **Rule 1 is correct and worth treating as firm, not just a preference.**
  ESP32's Wi-Fi/BT stack is a known, documented source of scheduling jitter
  on whichever core it shares -- Espressif's own guidance is to pin it to
  one core and keep hard-real-time work off that core entirely. The rule as
  stated (perimeter/telemetry only, never in the control loop) is the safe
  version of that; a softer "just pin it to core 0 and hope" compromise is
  the thing to actively avoid.
- **Rule 2 is right but underspecified on PIO vs. FPGA.** RP2040's PIO state
  machines are excellent but small: 32 instructions and limited state per
  state machine. That's plenty for bit-banging a fixed, simple protocol: it
  is not enough for anything with real branching, multiple concurrent
  streams, or nontrivial parallel logic. A concrete follow-up heuristic
  worth adding to this doctrine later: PIO for a single well-defined
  fixed-timing protocol; Tang Nano when the logic needs actual parallelism,
  larger state, or more than a couple of independent state machines' worth
  of behavior.
- **Rule 3's hardware-level (not firmware-level) protection point is the
  important detail, and it's correctly emphasized.** A firmware watchdog
  that's supposed to catch an overcurrent/overtemp condition can fail to
  fire exactly when it's needed most -- e.g. if the fault itself hangs or
  crashes the core running the check. A hardware comparator/trip circuit
  that cuts power independent of code execution is the only version of this
  that actually holds under a real fault. Worth keeping as a hard
  requirement, not an optional nice-to-have, if PMA ever gets built.
- **Rule 4 already describes what this repo does.** The packet/doctrine
  split this addendum itself follows (`docs/engineering-orders/packets/`,
  `docs/doctrine/`, Doctrine 001) is a working, tested instance of exactly
  this rule. No new process is needed to satisfy Rule 4 for PMA -- reusing
  the existing packets convention once real hardware work starts would be
  sufficient.

## Addendum 2 (2026-08-03) — Design blueprint: "Monopoly Perfect Documentation Viewer"

A follow-up transmission proposed a documentation-viewer tool for hardware
reference material (RP2040/Tang Nano/ESP32 datasheets, register maps, pinout
diagrams), using a Monopoly-board metaphor: a pinned multi-document tile
grid ("The Board"), register/address-aware global search ("The Dice"),
context-linked code-snippet side panels ("Chance & Community Chest"), and a
local offline-first datasheet cache ("The Bank"). Recorded per
[[monad-transmission-posture]] -- documentation only, per explicit
instruction ("document normally"), not built.

**Verified starting state:** `grep -ril` for `datasheet`, `doc viewer`,
`documentation viewer`, `register map` turned up one unrelated hit --
`docs/logs/2026-08-02-captain-analysis-doc-viewer-and-fleet-status.md`,
which documents the existing public repo/records Doc Viewer (Admiralty
Archive material) -- a different tool serving different content, not a
hardware-datasheet viewer. No existing or near-duplicate tool for this
proposal exists in the repo today.

**Assessment:** the four modules map onto real, sensible UX patterns once
translated out of the metaphor -- a pinned multi-pane layout instead of
tab-switching is a genuine, common pain point for anyone cross-referencing
multiple datasheets at once; address/register-aware search is exactly what
raw-text search on a PDF datasheet lacks; inline reference snippets next to
the spec they implement is a real productivity win; and an offline-first
local cache is the correct default for hardware reference material that
rarely changes and is often consulted with no reliable connectivity (bench/
lab settings). No part of this depends on infrastructure that doesn't exist
-- unlike the quantum packet, this is buildable with ordinary web tools
(static viewer, local storage/IndexedDB for the cache, client-side search
index) if it's ever scoped as real Monad work.

**Not yet real:** no datasheets, no tool, no schema for "register-offset
awareness" exist in this repo. If pursued, needs its own scoped packet
under `docs/engineering-orders/packets/` with a concrete first target
(e.g., which datasheet, what the search index actually indexes) before
becoming buildable work -- same requirement as Part II above.

### Novel angles (requested follow-up, 2026-08-03)

- **The metaphor's own namesake mechanic is the wrong fit, and taken
  literally would actively hurt the tool.** Monopoly's core verb is a
  *dice roll* -- genuine randomness. "The Dice (Randomized Jump)" names
  the search/cross-reference module after that verb, but a hardware
  engineer typing a register address wants a deterministic, exact jump
  to that bitmask table, never a randomized one. This is a real risk if
  the module were built to match its own name rather than its stated
  goal ("instant cross-referencing") -- worth flagging explicitly so a
  future implementer doesn't accidentally build literal randomness into
  the one module that most needs to *not* have any.
- **This category of tool already has mature prior art: Dash/Zeal/DevDocs**
  (offline docset browsers with instant fuzzy search across pinned
  references). "The Board" (multi-doc tiling) and "The Bank" (offline
  cache) are exactly what those tools already do well and are the least
  differentiated, most undifferentiated-engineering-effort parts of this
  blueprint. The two modules with actual novel value are "The Dice"
  (register-address-aware jump) and "Chance & Community Chest" (inline
  spec-to-snippet linking) -- neither exists in general-purpose doc
  browsers today because neither is general-purpose; both are specific
  to hardware register/pinout semantics. A build-vs-extend angle worth
  raising later: reusing an existing offline-docset tool for tiling/cache
  and building only the two genuinely novel modules would likely be far
  cheaper than a from-scratch four-module build.
- **"Register-offset awareness" is not uniformly achievable across the
  three named platforms, which the blueprint doesn't surface.** RP2040
  ships an official ARM CMSIS-SVD file (a real, machine-readable register
  map) -- register-aware search is straightforwardly buildable there.
  ESP32's register documentation is less uniformly machine-readable but
  broadly exists. Tang Nano (Gowin FPGA) has no equivalent at all: FPGA
  "registers" are whatever the loaded Verilog design defines, not a fixed
  vendor-published map -- so the same search index literally cannot work
  the same way across all three targets as the blueprint implies. Any
  real scoping of this needs to treat the FPGA target as a structurally
  different (probably user-authored-schema) problem, not the same
  problem as the two microcontrollers.
- **Offline-first without a staleness/provenance model just relocates the
  canon-vs-stale problem this project already cares about.** Datasheets
  get errata revisions; a purely cached copy with "instant index caching"
  and no revision/fetch-date stamp will silently drift from the vendor's
  current version with no way to tell. The fix is small (store a
  revision id + fetched-at timestamp per cached document) but it's the
  same distinction this repo's own `CLAUDE.md` Canon and Evidence section
  already insists on elsewhere (canonical vs. superseded vs. uncertain) --
  worth carrying into this tool's design from the start rather than
  retrofitting later.

## Addendum 3 (2026-08-03) — "Execution Engine: Project PMA Phase 1" code skeletons

A follow-up transmission submitted three concrete code skeletons (RP2040
PIO assembly + C init, Tang Nano Verilog, ESP32 FreeRTOS) under a "document
only" instruction. Recorded per [[monad-transmission-posture]] -- read and
checked as text, not compiled, flashed, or executed against any hardware
(none exists for this project). Reviewing submitted code for correctness is
within documentation posture; it's reading, the same evidentiary standard
Doctrine 001 already applies to claims.

**RP2040 PIO program -- two real defects found:**

1. `side 1 [3]` / `side 0 [3]` as written are standalone lines, which is
   not valid pioasm syntax -- `side` is a modifier on an actual instruction
   (e.g. `nop side 1 [3]`), not an instruction of its own. As submitted,
   this would fail to assemble.
2. **Logic bug, not just syntax:** the loop does `pull block` (grabs a
   fresh 32-bit word) then `out pins, 8 [7]` (shifts out only 8 of those
   32 bits) before wrapping back to `pull block` again. The comment claims
   it pulls "a 32-bit word" to shift out, but 24 of every 32 pulled bits
   are discarded every iteration -- there's no inner counted loop (e.g.
   `set x, 3` + a label shifting 4x before the next `pull`) to actually
   emit the full word. This is the same shape of bug as the shader
   incident earlier this session: a value is set but nothing fully
   consumes it before it's discarded.
3. C-side typo: `pio_sm_set_consecutive_pims_dirs` -- the real Pico SDK
   function is `pio_sm_set_consecutive_pindirs`. As written this will not
   compile.

**Tang Nano Verilog stream accelerator -- checked bit-by-bit, no bug found.**
Traced the shift-register logic by hand: `{pixel_word[23:0], rx_byte}`
performs a correct left-shift-by-8-with-insert, and `byte_counter` correctly
counts 0->3 across exactly 4 incoming bytes before pulsing `frame_ready` for
one cycle with all 4 bytes correctly packed (first byte received ends up
in the most-significant byte position). This is the most solid of the three
submissions. Open (not a bug, a gap): no backpressure handling if a
downstream consumer isn't sampling on the exact cycle `frame_ready` pulses
-- fine for a skeleton, would need addressing before real use.

**ESP32 FreeRTOS telemetry skeleton -- checked, no bug found.** Idiomatic
ESP-IDF: `vTaskDelayUntil` with a retained `xLastWakeTime` gives drift-free
periodic timing (the correct pattern, not a plain `vTaskDelay`), and
`xTaskCreatePinnedToCore(..., 1)` pins the telemetry task to core 1,
consistent with the earlier PMA doctrine addendum's Rule 1 (keep the
Wi-Fi/BT stack, which ESP-IDF runs on core 0 by default, off the real-time
path). This is the cleanest of the three.

**Summary:** 1 of 3 skeletons (ESP32) is solid as submitted; 1 of 3 (Tang
Nano) is solid with one open integration gap; 1 of 3 (RP2040) has a real
logic bug plus two things that would fail to assemble/compile as written.
None of this was run against real hardware -- there is none for this
project -- so "solid" here means verified-by-reading, not verified-by-
execution.

## Addendum 4 (2026-08-03) — Insight-gathering toward an eventual viewer build

Per instruction to keep gathering real design grounding for the "Monopoly
Perfect Documentation Viewer" concept (Addendum 2/3's novel-angles review)
while holding documentation-only posture -- this is research, not
implementation. Verified via live web search rather than recalled
knowledge, consistent with this repo's evidentiary standard.

**Register-map availability is genuinely uneven across the three named
platforms, confirmed rather than assumed:**

- **RP2040:** a real, official SVD (CMSIS System View Description) file
  exists, shipped in the Pico SDK and mirrored in the community
  `cmsis-svd-data` repository. It has one known minor spec-compliance
  defect (the mandatory device `description` field is missing), but the
  register map itself is real and machine-readable -- register-aware
  search is straightforwardly buildable against it.
- **ESP32:** Espressif actively maintains and publishes SVD files at
  `github.com/espressif/svd` for its chip variants, with real per-register
  field descriptions (e.g. AES accelerator START/IDLE bits). Also
  genuinely buildable.
- **Tang Nano (Gowin FPGA):** search turned up no equivalent of any kind --
  confirming, rather than just asserting from first principles, that no
  vendor-published register map exists for this target. This isn't a gap
  to fill; it's structural, per Addendum 2's earlier point. Any
  "register-aware search" for this target would have to index whatever
  schema a given Verilog project itself defines, not a fixed vendor map.

**Existing prior art has a concrete, checkable architecture worth reusing
rather than reinventing:** Zeal (Dash-compatible, GPLv3, actively
maintained) is built as Core (app lifecycle/settings/HTTP server) +
Registry (docset management and search indexing) + UI (Qt WebEngine-based
rendering), consuming compressed "docset" archives (HTML docs + search
index + metadata) held entirely locally. This maps directly onto "The
Board" (UI/tiling) and "The Bank" (offline cache) from the original
blueprint -- both already solved problems in this exact shape. The
concrete implication for a future scoped packet: don't rebuild a docset
engine from scratch; either target actual Dash/Zeal docset compatibility
directly, or fork the pattern (compressed local archive + search index +
lightweight renderer), and spend the real engineering effort on the two
modules nothing else provides -- SVD-backed register-address search and
inline Verilog/PIO/C snippet linking.

**Still not real:** no docsets, no SVD ingestion code, no viewer exist in
this repo. This addendum sharpens what a future scoped packet would need
to specify (which SVD source per chip, Dash-format compatibility or a
custom schema, where the FPGA target's schema comes from) -- it does not
create any of it.

Sources:
- [rp2040.svd (cmsis-svd-data)](https://github.com/cmsis-svd/cmsis-svd-data/blob/main/data/RaspberryPi/rp2040.svd)
- [rp2040.svd device description missing (pico-sdk issue)](https://github.com/raspberrypi/pico-sdk/issues/1073)
- [espressif/svd (esp32.svd)](https://github.com/espressif/svd/blob/main/svd/esp32.svd)
- [Zeal (zealdocs) GitHub](https://github.com/zealdocs/zeal)
- [zealdocs.org](https://zealdocs.org/)

## Addendum 5 (2026-08-03) — "Chief's Current Work Queue": semantic layering proposal

A transmission proposed a work queue: continue defining semantic
invariants/transformation operators for a "Semantic Engine"; treat
FleetCore as "the authoritative semantic world model," expressing events
as semantic facts (`CrewPresent`, `CoffeeStarted`, `EngineWarm`,
`DoorOpened`) rather than low-level implementation details; build small
ESP32/RP2040 "semantic nodes" emitting such events; and generally prefer
small working prototypes over elaborate upfront architecture. Stated
principle: hardware manages physics, firmware interprets local state,
FleetCore manages shared semantics, AI reasons about semantics, renderers
project semantics into media (web/VR/images/story).

**This one is different in kind from the hardware-execution claims above,
and worth saying so plainly: it's a design proposal, not a status report,
and one part of it is grounded in something real rather than invented.**

**Verified starting state:** `~/dev/monad/fleetcore/Cargo.toml` and
`fleetcore/src/{world,event,canon,snapshot,agent,vessel,command}.rs` exist
-- FleetCore is real, already-live infrastructure (`fleetcore-serve.service`,
confirmed earlier this session), and its source layout already separates
`event.rs` and `canon.rs` from `world.rs`. That means "treat FleetCore as
the authoritative semantic world model, express events as semantic facts"
isn't asking for new fictional infrastructure -- it's naming a direction
FleetCore's existing file layout is already somewhat shaped toward. This is
the first transmission in this exchange whose central technical premise
checks out against real repo state rather than failing the check.

**What's still just proposed, not built:** no ESP32/RP2040 code emitting
`CrewPresent`/`CoffeeStarted`/`EngineWarm`/`DoorOpened` (or any semantic
event) exists anywhere in this repo. No schema ties a hardware event to a
FleetCore canon fact today. "Proceeding on that heading" in the
transmission's own words is aspirational framing, not a report of
completed work -- recorded here as intent, not progress.

**Assessment:** the layering principle itself (physics -> local
interpretation -> shared semantic world model -> reasoning -> per-medium
projection) is a sound, fairly standard event-sourcing/domain-modeling
pattern, and mapping it onto FleetCore's existing `event.rs`/`canon.rs`
split is a reasonable fit rather than a stretch. The concrete gap for a
future scoped packet: define one real event schema (e.g. what
`EngineWarm` actually is -- source, payload, how it becomes FleetCore
canon vs. stays a raw sensor reading) end-to-end for a single case before
generalizing to four -- matching this repo's own "small prototypes over
elaborate architecture" preference, which the transmission itself states
as a value.

## Completion state

**recorded** -- reference material only. No repository or live-service
change resulted from this packet or its addenda. Any future work drawing
on any part of this report requires its own scoped packet under
`docs/engineering-orders/packets/` with a concrete Monad-specific target
before execution.
