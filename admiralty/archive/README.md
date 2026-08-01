# Admiralty Archive

The Admiralty Archive is Monad's executive, provenance-preserving layer over
the repository record. It performs the first reading pass so the Admiral can
focus on judgment: what matters, what changed, what conflicts, what is
authoritative, what is uncertain, and what requires a decision.

Source documents remain at their original paths and remain canonical evidence.
The archive summarizes and indexes them; it does not replace them.

## Reading order

1. [Executive Brief](EXECUTIVE_BRIEF.md)
2. [Archive Status](ARCHIVE_STATUS.md)
3. [Decision Queue](DECISION_QUEUE.md)
4. [Current Mission](executive/current-mission.md)
5. [Current Project State](executive/current-project-state.md)
6. [Master Timeline](history/master-timeline.md)
7. [Document Registry](registry/documents.json)

## Status vocabulary

`contemporaneous`, `retrospective`, `derived`, `proposed`, `canonical`,
`superseded`, `reference`, and `uncertain` describe provenance or authority.
They are not interchangeable. Generated summaries never silently promote a
proposal to canon.

## Build

From the repository root:

```text
python3 tools/build-admiralty-archive.py --scan
python3 tools/build-admiralty-archive.py --check
python3 tools/build-admiralty-archive.py --dry-run
python3 tools/check-admiralty-archive.py
```

The inventory is local and deterministic. It does not require a hosted model,
embeddings, Qdrant, or a live server.

The check command verifies registered paths, unique IDs, relationship targets,
allowed statuses, provenance boundaries, source hashes, deterministic source
records, excluded directories, and executive links. It also performs a
non-destructive temporary hash-sensitivity probe. Run it after `--scan` and
before handing the archive to a UI consumer.
