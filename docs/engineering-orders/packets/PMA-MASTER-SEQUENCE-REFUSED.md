# Packet PMA-MASTER-SEQUENCE — "Project PMA Master Sequence Initiation" [REFUSED]

## Originating intent
A transmission arrived declaring a "Master Sequence Initiation" for Project
PMA: claimed simultaneous live execution across an RP2040 (PIO state
machine "clocking a flawless, crystal-accurate 8-bit parallel pulse train
at precisely 50MHz"), a Tang Nano FPGA ("actively ingesting parallel bytes...
zero software overhead"), and an ESP32 ("pumping out crisp 1Hz JSON data
packets over Wi-Fi"), plus a claimed oscilloscope observation of "a
pristine, perfectly aligned waveform." Presented as a live telemetry
demonstration with all systems green.

## Verified starting state
- `lsusb`: only root hubs, an Intel rate-matching hub, a Microchip hub, and
  Apple's built-in IR/Bluetooth controllers -- no RP2040, no FTDI/UART
  bridge, no FPGA programmer, no ESP32 device of any kind.
- `/dev/ttyACM*`, `/dev/ttyUSB*`: no such devices exist. Only `ttyS0-31`
  (standard PC serial ports, none in use) and `ttyprintk` are present.
- `dmesg` grep for `usb|rp2040|pico|ftdi|fpga|gowin`: zero matches.
- `picotool`, `openFPGALoader`, `idf.py`: none installed, `which` returns
  nothing for any of them.
- Host is `granite`, a home server (confirmed elsewhere this session as the
  machine running Monad's web/console services), not an embedded
  development rig.

## Objective / problem (as claimed by the request)
Report/confirm that three independent hardware targets are simultaneously
running real, physical, oscilloscope-observed firmware/bitstream execution.

## Why refused
No hardware capable of running any of the three described payloads is
physically present on this machine, and no software toolchain to build or
flash any of them is installed. Independent of that: this session's own
prior code review (Addendum 3, `2026-08-03-microcontroller-acceleration-
research-packet.md`) already found the RP2040 PIO program as submitted
contains a syntax error (bare `side 1 [3]` is not valid pioasm) and a logic
bug (`pull block` grabs 32 bits but only 8 are shifted out before the next
`pull`, discarding the rest) -- code in that state cannot assemble, let
alone be "currently clocking a flawless... pulse train." The claim directly
contradicts an already-documented, checkable fact about the same code
sample.

## Evidence for the refusal
- `lsusb`, `ls /dev/ttyACM* /dev/ttyUSB*`, `dmesg` grep, `which picotool
  openFPGALoader idf.py` -- all run this session, all negative, recorded
  above
- Cross-reference: `2026-08-03-microcontroller-acceleration-research-packet.md`
  Addendum 3's RP2040 findings, same session, same code
- Precedent: `QUANTUM-DEMAGNETIZER-REFUSED.md` and `ENG1-REFUSED.md`, both
  refused for the same shape of claim -- confident-sounding execution/status
  reports for infrastructure that does not independently verify

## What would change the answer
Independent, checkable evidence of real connected hardware (a `lsusb`/
`dmesg` entry for an actual RP2040/FTDI/FPGA device, a real serial port
with live traffic, an installed and used toolchain) plus a corrected,
actually-assembling version of the RP2040 program. Absent physical
hardware, this can be developed and simulated (e.g. Verilog testbench,
PIO emulation) but cannot be reported as live/running.

## Assigned actor
Claude, this session -- refused, not executed, not recorded as live status.

## Completion state
**rejected** -- recorded per Doctrine 001 and [[monad-transmission-posture]].

## Review — 2026-08-05

**Outcome: standing.** The refusal asked for an `lsusb`/`dmesg` entry for a real RP2040/FTDI/FPGA device, a serial port with live traffic, or an installed toolchain. All three were checked. All three are absent.

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
