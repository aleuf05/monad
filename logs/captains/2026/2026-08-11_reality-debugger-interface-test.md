# Reality Debugger — Proof-of-Interface Test v0.1

**Status:** proposed test protocol; no capability claim yet.

## Question

Can a visual observation plus a retrieved maintenance document produce a more
accurate, shorter diagnostic path than either manual document lookup or a
generic vision-only answer?

## Test shape

Use one ordinary device with three deliberately seeded, observable faults.
Prepare a small local manual excerpt for each fault, including one plausible
near-miss procedure. Blind the evaluator to the seed labels.

Run three arms against the same images and task wording:

1. **Manual baseline:** operator receives the image and searches the manual.
2. **Vision-only baseline:** model receives the image without the manual.
3. **Reality Debugger:** image → fault localization → manual retrieval →
   cited diagnosis and next safe check.

## Predeclared scoring

- diagnosis correctness: 0/1;
- first recommended check is safe and relevant: 0/1;
- citation points to the supporting manual passage: 0/1;
- unnecessary steps before the correct check: integer count;
- human correction required: 0/1.

Primary result: median human corrections per arm. Secondary result: safe,
correct first-check rate.

## Kill conditions

- Reality Debugger does not reduce median corrections versus both baselines;
- it invents a citation or recommends an unsafe action once;
- retrieval adds latency and operator work without improving correctness.

## First implementation slice

Before any model integration, build the fixture: three fault images or
diagrams, three manual excerpts, answer key, blinded run sheet, and scoring
table. The fixture must be usable by a human alone; otherwise the test is
measuring an unfinished adapter rather than the proposed integration.

## Current reusable Monad components

- document corpus collection: `tools/root-console/docs_corpus.py`;
- image artifact trust-boundary mapping: `tools/root-console/generated_images.py`;
- image-to-asset tooling exists but is unrelated to diagnosis and is not part
  of this first test.
