# Mission

Build Harbormaster as a small, maintainable project inside the Monad repository.

Harbormaster should help make fleet operations easier to understand, operate, or review. It should be implemented only after this document has been read and the active requirements are confirmed from the project specification and Captain G's briefing.

# Context

Harbormaster lives under `projects/harbormaster/`.

The repository is already prepared with briefing and planning documents. This project is independent from the public Monad website, Bridge, Doctrine, Qdrant, agents, deployment automation, and other production systems unless Lieutenant cgl explicitly expands scope.

The current sprint begins from documentation only. No implementation assumptions should be carried in from chat unless they are also represented in repository files.

# Objective

Create the smallest useful Harbormaster implementation that satisfies the accepted sprint packet.

The implementation should be simple, auditable, and easy for Lieutenant cgl to run locally. Prefer boring architecture over clever architecture.

# Requirements

- Read `SPEC.md`, `CAPTAIN_G.md`, `TODO.md`, and this file before implementation.
- Keep work contained under `projects/harbormaster/` unless Lieutenant cgl gives explicit approval.
- Use the simplest workable technology for the accepted task.
- Prefer plain files, local execution, and clear status output.
- Keep documentation current as implementation decisions are made.
- Record meaningful sprint events in `WATCH_LOG.md`.
- Update `TODO.md` as tasks move from pending to complete.
- Preserve maintainability over novelty.

# Constraints

- Do not add unnecessary dependencies.
- Do not add a package manager unless the accepted implementation requires it.
- Do not connect to Monad production systems by default.
- Do not touch Bridge, Doctrine, Qdrant, agents, deployment scripts, or the public website unless explicitly ordered.
- Do not commit, push, deploy, or modify git history unless Lieutenant cgl explicitly orders it.
- Do not store secrets, API keys, credentials, private network details, or local machine configuration.
- If uncertain, choose the simpler implementation and document the assumption.

# Acceptance Tests

Acceptance tests must be defined before implementation work is considered complete.

At minimum, Gemini CLI should verify:

- The project can be run from a clean checkout using the documented instructions.
- The implementation performs the requested core behavior.
- The implementation fails clearly when required inputs are missing.
- The README explains how to start, test, and inspect the project.
- `WATCH_LOG.md` records the implementation watch.
- `TODO.md` reflects the completed sprint state.

# Deliverables

Gemini CLI should report:

- Files created or modified.
- Commands run.
- Tests performed and results.
- Any assumptions made.
- Any risks or follow-up work.
- Suggested commit message.
