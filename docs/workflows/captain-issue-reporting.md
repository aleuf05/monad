# Captain Issue Reporting

Every substantial Monad engineering order ends with a Captain-facing issue
report. This is a standing closeout requirement, not an optional artifact.

## When to write one

Create or update the report whenever work includes any of the following:

- a new subsystem or public surface;
- persistence, replay, shared state, or authority changes;
- a deployment or privileged commissioning handoff;
- defects, operational warnings, or unresolved design work;
- parallel delegated engineering;
- a readiness recommendation.

Small documentation-only corrections may update the most recent report rather
than creating a new one, provided the status remains accurate.

## Location and naming

Store reports under:

```text
docs/reports/YYYY-MM-DD-captain-issue-report.md
```

If several major orders close on the same date, include the order name:

```text
docs/reports/YYYY-MM-DD-<order>-captain-issue-report.md
```

The final operator message must include a clickable local link to the report.

## Required sections

Each report states, in plain operational language:

1. Executive status.
2. Action required from the Lieutenant or Captain.
3. Active engineering issues, with GitHub links where available.
4. Deployment or commissioning gates.
5. Resolved findings.
6. Validation evidence and exact test counts where meaningful.
7. Deferred risks or evidence gaps.
8. One recommended next action.
9. A readiness statement when the engineering order defines one.

Separate code defects from activation gates, accepted limitations, historical
notes, and unrelated host maintenance. Do not inflate the active issue list by
repeating findings already fixed and regression-tested.

## Evidence rules

- Reconcile the report against current services, Git, GitHub issues/PRs, and
  the latest verification documents before publication.
- Mark stale findings as resolved; retain enough history to explain what
  changed.
- Link active issues rather than duplicating their full design discussion.
- Record whether privileged work is merely staged or actually completed.
- Never claim live readiness from source-level tests alone when a service still
  runs an older binary.
- Preserve rejected commands and failed checks in the record.

## Publication and commissioning

The report is part of the integrated change:

1. Commit and publish it.
2. Merge its PR or include it in the engineering-order PR.
3. Confirm the repository is clean.
4. Repin `/home/cgl/cmd.sh` to the final report-bearing commit if privileged
   commissioning remains.
5. Provide the Captain a clickable link and the exact remaining action.

If later verification changes the conclusion, update the report and repeat the
publication/repin sequence. The report must describe current truth at handoff,
not the truth from an earlier test pass.

## Standing outcome

An engineering order is not administratively closed until the Captain can open
one report and see what changed, what remains, what evidence exists, and what
decision or action comes next.
