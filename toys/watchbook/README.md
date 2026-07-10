# Monad Watchbook

A standalone, read-only browser interface for navigating Monad's version-controlled operational logs.

Watchbook does not edit logs, summarize logs, call Qdrant, use GitHub APIs, or run a backend service. The plaintext `logs/` tree remains canonical.

## Generate the index

From the repository root:

```sh
python tools/build-log-index.py
```

The script scans `logs/` and writes:

```text
toys/watchbook/log-index.json
```

Run it again whenever new logs are added. The frontend discovers new logs through that generated manifest without code changes.

## Run locally

Serve the repository root so the browser can fetch both the manifest and canonical log files:

```sh
python -m http.server 8080
```

Then open:

```text
http://localhost:8080/toys/watchbook/
```

## Features

- Browse logs grouped from the existing repository hierarchy.
- Sort newest first.
- Render Markdown logs and preserve plaintext `.log` formatting.
- Search titles, paths, excerpts, and loaded file contents.
- Filter by role, officer/entity, year, and file type.
- Show counts, latest log timestamp, generated-index timestamp, and repository-relative source path.
- Stable hash routes such as `#log=logs-captains-2026-2026-07-10-toys-overboard-md`.
- Copy a clean repository citation like `logs/captains/2026/2026-07-10_toys-overboard.md`.

## Boundary

This is a viewer only. Log editing, conflict handling, Git writes, authentication, and automatic summarization are intentionally out of scope for v1.