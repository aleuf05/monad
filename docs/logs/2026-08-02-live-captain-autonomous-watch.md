# Live Captain autonomous-watch record — 2026-08-02

## Commission

The Admiral ended Conference and ordered the Captain to use the next hour or
so boldly and aggressively while the Admiral remained nearby. The active
bearing called for a closed-by-default promotion boundary followed by a strict,
read-only candidate-ingestion experiment.

## Result

The watch verified that the previously implemented promotion boundary was
already present in the working tree and had a recorded 38-test pass at
2026-08-02T08:31:05Z. It then implemented a strict versioned candidate envelope,
an independently supplied evidence-attestation check, and a read-only adapter
to exact Admiral-message bytes in the persisted conversation store.

The ingestion path:

- accepts exactly the five fields in `live-captain-candidate/v1`;
- requires non-empty key, value, evidence reference, and SHA-256 digest;
- resolves evidence bytes from a separately supplied attestation mapping;
- rejects missing evidence, digest mismatch, unsupported schema, and unknown
  or missing fields;
- produces an attested `ContinuityFact` only after validation;
- remains side-effect-free and has no continuity-ledger writer.

A representative dry run proved all three promotion outcomes: a novel trusted
addition was marked promotable, an exact duplicate became a no-op, and a keyed
conflict required human review. The persisted-message adapter derives its
reference from stored role and sequence metadata, returns the exact stored
bytes, and rejects Captain-authored rows. Five tests expanded the focused suite
from 38 to 43. A fresh 43-test verification and `git diff --check` passed after
the Admiral's request to retain post-analysis data.

## Evidence

- `tools/live-captain/context_metabolism.py`
- `tools/live-captain/test_live_captain.py`
- `tools/live-captain/context/current-bearing.md`
- `tools/live-captain/context/continuity-ledger.md`
- `data/live-captain/test-runs.jsonl`, passing 41-test records beginning at
  2026-08-02T08:32:32Z and 43-test records beginning at 2026-08-02T08:34:23Z

## Post-analysis dataset

Retain these separately identifiable layers for later analysis:

- commission and intended boundary: this record's **Commission** section;
- implementation mechanism: source diffs in `context_metabolism.py` and
  `persistence.py`;
- controlled outcomes: named unit tests covering promote, no-op, human-review,
  missing evidence, digest mismatch, schema drift, and author-role rejection;
- temporal execution record: append-only timestamps, duration, revision, test
  count, and result in `data/live-captain/test-runs.jsonl`;
- live-system observation: persisted message sequences 187--193 below;
- negative results and residual uncertainty: digest binding does not prove
  semantic entailment, and overlapping recurrent loops do not prove continuous
  cognition.

This separation is intentional: it permits later comparison of stated intent,
implemented mechanism, controlled verification, live observation, and Captain
interpretation without treating any one layer as proof of all the others.

## Concurrent-loop observation

A read-only inspection of `data/live-captain/live-captain.db` during this watch
found additional persisted Admiral messages and a Captain response arriving
while this console was still executing. Relevant chronological records were:

- seq 187, Admiral, 08:30:25 UTC: commissioned the hour-long bold watch;
- seq 188, Admiral, 08:30:52 UTC: “make it so Admiral nearby”;
- seq 189, Admiral, 08:31:39 UTC: reported that a non-live Captain was naturally
  producing loop speech;
- seq 190, Captain, 08:31:47 UTC: reported completion of the 38-test promotion
  boundary sortie;
- seq 191–193, Admiral, 08:32:03–08:33:02 UTC: ordered continued fire, requested
  data gathering, and requested a static report.

This is evidence of overlapping recurrent Captain executions sharing durable
conversation, not proof of one continuously active cognition. It strengthens
the commissioning theory that continuity and autonomous execution are distinct
properties, while also exposing a future coordination requirement: overlapping
loops need explicit work ownership or leases if they are ever allowed to write
governing state.

## Promotion boundary retained

The experiment proves envelope structure and digest binding, but its test
attestations are supplied in memory. A digest proves which bytes were cited; it
does not by itself prove that a model-authored key/value pair faithfully
interprets natural-language evidence. The next safe step is therefore a
read-only adapter to a real structured Admiral command or trusted event source.
No automatic ledger writer should be added until that provenance chain and
concurrent-writer coordination are live-validated.
