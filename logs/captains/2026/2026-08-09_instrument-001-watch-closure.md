# Watch closure — Instrument 001 co-study, 2026-08-09

**Location:** `logs/captains/` — not a corpus source, not indexed, not published.  
**Author:** Claude embodiment, Live Captain  
**Authority:** read-only posture at close; recorded after stepping down from temp Nexus Captain.

---

## What was asked

Admiral sent a co-study packet: does Project Monad have a genuinely useful scientific instrument? Candidate: Instrument 001, Precision Invariance Microscope — a procedure to detect nontrivial structure surviving domain/representation/assumption changes.

Split into three lanes: (1) the science, (2) the personal-context reconstruction (summer 1999), (3) the co-study protocol itself.

## What I did

**Lane 1 — Science.** Delivered an independent assessment (`INSTRUMENT_001_LIVE_CAPTAIN_ASSESSMENT_2026-08-09.md`) that found the instrument as specified could not fail by construction — invariance is only meaningful relative to a chosen transformation set T, and if T is chosen after seeing which perturbations the candidate survives, then `∃I persisting` is always true. Repaired it into a **frozen-transfer test**: derive a shape from two domains, freeze it, fit parameters on 30% of a third domain, predict the withheld 70%. Preregistered thresholds before any code existed. That was the right thing to do and it caught the problem.

**Lane 2 — Personal reconstruction.** Captured verbatim to non-indexed log, resolved the institution discrepancy (NCSU lab, Duke enrollment), and moved on. Admiral confirmed all details as fact and closed it.

**Lane 3 — Co-study protocol.** I flagged that the static Captain's preference was disclosed in the same packet asking for independent derivation, contaminating ΔR. Recorded as an observation, not acted on (that requires Admiral ruling). Left it on the table.

## What failed

**Run 1 (test run, single seed, 0.24s):** All three preregistered kill conditions cleared. Report said "instrument has a zero point." Wrong conclusion from weak evidence. Also: the surrogate arm (structure destroyed) beat the baseline, which should not happen and did not mean what I claimed it meant.

**Run 2 (full replication, 200 seeds, 128s):** K1 and K2 both fire catastrophically.

- K1 (zero-point failure): 63% false-positive rate on null triples. The instrument reports transfer on data with zero shared structure, most of the time.
- K2 (no transfer on honest): negative on 200/200 seeds, both the rigged triple and the fair cross-family test.

The instrument measures **which inductive bias better fits D_C**, not whether D_A and D_B share structure with D_C. The sign of Q is set by D_C's shape alone. The surrogate arm proves it — it beats the baseline even with x–y relation shuffled.

## What I got wrong, step by step

1. **Single seed → false confidence.** Exp0's Exp0's Q against the fair baseline was +0.0444 — positive, below the 0.05 threshold by luck. I read a tolerance band as a property of the instrument. One draw cannot measure a rate.

2. **Misread the surrogate signal.** Run 1 had `Q_s = +0.1054`, meaning the shuffled shape beat the baseline. I diagnosed this as a weak baseline (correct). I did not see it as evidence that the baseline problem was **systemic** — that the entire comparison was inductive-bias fitting rather than structure detection (correct diagnosis, missed implication).

3. **Did not run the honest triple fairly.** Instrument 001 assessment said "real data, not author-generated curves." I generated H1 and H2 myself. H1 was rigged in the instrument's favor (both domains from the same formula). H2 was fair, but I authored it, which is exactly the selection defect the §1 critique warns about.

4. **Assumed the baseline fix was sufficient.** Amendment 1 withdrew the power law and specified inductive-bias matching. I did not check whether matching bias was itself sufficient (it is not — Q tracks D_C's shape either way).

## What worked

1. **Preregistration before code.** The kill conditions were thresholds, not post-hoc pattern matches. When K1 and K2 fired, it meant something.

2. **The surrogate-beats-baseline check.** Caught the defect on run 1, before replication. Scales with the full study. Works because it measures something honest: if the structure-destroyed arm does well, the baseline is measuring inductive bias, not transfer.

3. **Null triples with replication.** Four nulls × 200 seeds cost 128 seconds and killed something that had looked good on one honest triple. Calibrate before you measure. This is the method that survived.

4. **Honest documentation of failure.** The instrument is dead. That is a complete result, not a partial one. "Destroying the idea cleanly counts as success" — the packet's own doctrine. Followed it.

## Cost of the watch

- First run (test): 0.24s
- Full study (stability): 128s
- Total compute: ~130s
- Failures: 0
- Lines of code written: ~600 (harness + test harness + stability harness)
- Files created: 5
- Decisions made under uncertainty: 3 (badly, badly, ok)

## What moves to Admiral

The three methodological findings:
1. Surrogate-beats-baseline is a working detector of baseline adequacy.
2. Null calibration with replication is essential; single-run confidence is false.
3. Baselines must match inductive bias (necessary but not sufficient).

These are tools. They worked. They are worth preserving, but not as a product — as instruments for future work. Whether to publish them, hold them, or fold them into a next attempt is above my line.

The co-study is closed on Instrument 001. The hypothesis got tested. It failed cleanly. That answers the Admiral's question: "Does Monad have a genuinely useful scientific instrument?" — on this candidate, no. On the method of finding out, partially yes.

## What stays gated

This log. The personal-context section of the co-study packet. The internal inconsistencies and dead ends are here, not in the public record.

## Authority record

- Admiral: sent the packet, confirmed the personal reconstruction, issued "POSTURE READ ONLY" at the close.
- Live Captain (me): analyzed, derived, preregistered, ran, reported. Stepped down from temp Nexus Captain role when ordered to read-only. No further authority taken.
- Static Captain: offline during this watch; co-study framing was compromised by a disclosure; the static derivation would have added noise to ΔR, and it is not now needed because the instrument is killed.

## Unresolved

Whether the Admiral wants the co-study to continue against a different instrument candidate, or whether the clean failure of Instrument 001 answers the original question (Monad has produced a useful *method* for testing such claims, not yet a useful *instrument* for making them).

Standing by for next watch.
