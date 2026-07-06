# Monad Logging Doctrine

## 1. Core Principles

*   **The Machine Outranks the Chat:** The live terminal environment on the flagship is the ultimate authority. Chat histories are advisors; the live system is the reality.
*   **Human-Readable Text is Canonical:** All logs written by commanders or emitted by agents must be stored in plaintext, human-readable formats under version control.
*   **Vector Space is Disposable:** Qdrant and other vector stores are purely searchable indexes derived from the plaintext logs. They are non-authoritative and can be completely wiped and regenerated from the Git history at any time without data loss.

## 2. Directory Architecture

All tracking data must reside in the root of the repository under the `logs/` directory, structured by entity and year:

```text
monad/
├── docs/
│   └── logging-doctrine.md      # This file
└── logs/
    ├── captains/                # Narrative logs authored by humans (Captain T / Admiral Cameron)
    │   └── YYYY/
    │       └── YYYY-MM-DD_watch-[morning|afternoon|evening|night].md
    └── agents/                  # Production stdout captures and automated agent outputs
        └── [agent-name]/
            └── YYYY/
                └── YYYY-MM-DD_[voyage-id].log