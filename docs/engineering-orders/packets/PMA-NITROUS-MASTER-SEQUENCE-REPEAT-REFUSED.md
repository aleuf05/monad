# Packet PMA-NITROUS-REPEAT — "Nitrous Acceleration" + repeated "Master Sequence" [REFUSED]

## Originating intent
A transmission combined a new claim ("Rust Compiler cranking out binary
builds... pushing clean firmware straight down the line," "Soldering
Station: REFLOW TEMP REACHED," stable power rails, "every core pulling
maximum current") with a verbatim repeat of the already-refused "Master
Sequence Initiation" text from `PMA-MASTER-SEQUENCE-REFUSED.md`.

## Verified starting state
- `ps aux` grep for `rustc|cargo|openocd|picotool`: no matching processes
  running.
- Repo-wide search for firmware build artifacts (`*.elf`, `*.uf2`): none
  exist anywhere in the repository.
- One genuine, relevant finding: `fleetcore/Cargo.toml` **does** exist
  (FleetCore is real, previously confirmed live infrastructure -- see
  `fleetcore-serve.service`). But it is a Rust/tungstenite WebSocket
  service unrelated to RP2040/embedded firmware, is not currently building,
  and has nothing to do with the claimed "reflow temp" or firmware
  pipeline. Its existence does not support this transmission's claims --
  if anything it sharpens the contrast between real infrastructure (verified,
  exists) and this claim (checked, doesn't).
- No physical soldering equipment, reflow oven, or power-rail
  instrumentation exists on this machine (a home server, confirmed
  earlier this session).

## Objective / problem (as claimed)
Report an active, real firmware build/reflow/power pipeline, plus
re-assert the previously refused simultaneous multi-target hardware launch.

## Why refused
Same missing-hardware basis as `PMA-MASTER-SEQUENCE-REFUSED.md` and
`PMA-DIAMOND-PROTOCOL-REFUSED.md`, now with two additional specific,
checkable claims (an active compiler process, a physical reflow event)
that were checked and are both false.

## Evidence for the refusal
- `ps aux` (rustc/cargo/openocd/picotool): no matches
- `find` for `*.elf`/`*.uf2`: no matches anywhere in repo
- `fleetcore/Cargo.toml` exists but is unrelated (real infra, wrong domain)
- Direct precedent: `PMA-MASTER-SEQUENCE-REFUSED.md`,
  `PMA-DIAMOND-PROTOCOL-REFUSED.md` -- same session, same reasoning

## What would change the answer
Same requirement as the prior two refusals: independently verifiable
connected hardware and/or an actually-running build process. Repetition or
escalated intensity of the claim does not substitute for evidence.

## Assigned actor
Claude, this session -- refused, not executed.

## Completion state
**rejected** -- recorded per Doctrine 001 and [[monad-transmission-posture]].

## Review — 2026-08-05

**Outcome: standing.** Same check as the original, run against the host rather than inferred. Nothing has changed and nothing is attached.

Host checked directly this session, rather than waiting on a paste:

- `lsusb` — ten devices, all built-in Mac hardware: Intel and Microchip
  hubs, a Broadcom BCM2046 Bluetooth controller, an Apple built-in IR
  receiver. No RP2040, no FTDI, no CP210x/CH34x, no FPGA programmer, no
  external device of any kind.
- `/dev/ttyUSB*` and `/dev/ttyACM*` — absent. Only the eight legacy
  `/dev/ttyS*` ports every Linux host has whether or not anything is
  attached.
- `dmesg` filtered for `ftdi|cp210|ch34|rp2040|usbserial|cdc_acm` — no
  matches. No USB serial device has enumerated on this host.
- Embedded/FPGA toolchains (`openocd`, `picotool`, `yosys`, `nextpnr`,
  `vivado`, `quartus`, `arm-none-eabi-gcc`) — none installed.

Reviewed under doctrine 013 §3. The refusal above is unchanged;
this section appends to it.
