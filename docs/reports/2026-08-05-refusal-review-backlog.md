# Refusal review backlog — first full pass

Date: 2026-08-05
Scope: all 18 refusals in `docs/engineering-orders/packets/`, reviewed
under doctrine 013 §3. None had been reviewed before; all 18 now carry a
dated `## Review` section. No refusal text was edited — reviews append.

## Outcomes

| Outcome | Count | Packets |
|---|---|---|
| moot | 1 | Codex emergency kill |
| standing (terminal) | 4 | Crystal Ledger ×2, special-mode toggle, input override |
| standing — evidence checked | 6 | master sequence, nitrous repeat, chrono jump, diamond protocol, quantum demagnetizer, VENNA |
| standing — needs one concrete sentence | 5 | mission reanchor, documentation posture, permissive state ×2, ENG1 |
| resolved (same day, see below) | 2 | LUCA pair |

## The change worth noting

The hardware bucket was carried as "waiting on an `lsusb` paste from the
Admiral." It did not need one. `lsusb`, `/dev/tty*`, `dmesg`, and a
toolchain check are read-only local inspection this session can run
itself, and it did:

- Ten USB devices, every one built-in Mac hardware — Intel and Microchip
  hubs, a Broadcom BCM2046 Bluetooth controller, an Apple IR receiver.
- No `/dev/ttyUSB*` or `/dev/ttyACM*`. No `dmesg` match for
  `ftdi|cp210|ch34|rp2040|usbserial|cdc_acm`.
- No `openocd`, `picotool`, `yosys`, `nextpnr`, `vivado`, `quartus`, or
  `arm-none-eabi-gcc` installed.
- `pgrep -af codex` returns nothing.
- Zero implementing `.py`/`.js`/`.html`/`.service` files for VENNA,
  AROMONAS, LUCA, or Crystal Ledger. They appear only in packets
  describing them.

Those refusals now rest on a check that was run, not on a check that was
never possible. That is a real upgrade in the quality of the record even
though not one outcome changed.

The general lesson, and the reason this took an hour rather than a week:
**a blocking condition phrased as "the Admiral must supply X" is worth
re-reading for whether X is actually his to supply.** Four of the five
hardware conditions were answerable from the host.

## Terminal

Four refusals are marked `standing (terminal)`. This is a new label and it
means: the review loop is closed, not the subject. These four turn on
structural objections — a premise that is incoherent rather than
unverified, or a term that no observation could satisfy. Re-running the
review costs effort and cannot change the outcome, so they leave the
periodic backlog. Any genuinely different request is a new packet, not a
review of these.

## What remains open, and who can close it

- ~~**2 packets** (the LUCA pair)~~ — **resolved 2026-08-05.** The Admiral
  confirmed in conference, out of character, that the research is
  genuinely wanted. Both refusals now carry a second review; the research
  is filed as `2026-08-05-luca-code-standardization-research.md`. VENNA
  was the precedent and it held.

  One thing learned worth carrying: two figures the packets gave without
  sources turned out to be real and citable. The submitted material was
  carrying good science under bad packaging, and the packaging is what
  got it refused. Worth checking a packet's *numbers* even when its
  framing is unacceptable.
- **5 packets** need one or two sentences naming something concrete — a
  file, a feature, a fix. None of them is a standing objection to the
  underlying want; each is a request for enough specificity to build from.
  ENG1 is the easiest: it names no host, so naming one converts it from
  unverifiable to testable in a single step.

Nothing in this backlog is blocked on work. It was blocked on eight
sentences; the Admiral wrote one of them the same day and it cleared two
packets. Five remain, each needing a concrete noun rather than a
decision.
