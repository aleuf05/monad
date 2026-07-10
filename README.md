# Monad

**Monad is a human-directed software engineering experiment for building durable software artifacts with AI-assisted teams.**

The project explores a simple question:

> What changes when AI systems are treated not as isolated chatbots, but as participants in a disciplined engineering organization?

Monad combines human direction, specialized AI roles, explicit engineering packets, operational logs, and version-controlled artifacts. The goal is not to remove the human from software development. The goal is to make collaboration between humans and AI more repeatable, inspectable, and useful over time.

## Why Monad Exists

Most AI-assisted development happens inside short-lived conversations. Useful decisions disappear into chat history, context is lost between sessions, and work becomes difficult to continue or audit.

Monad treats the repository as the durable memory of the organization.

Conversations are working memory. The repository is the record.

Ideas become plans. Plans become implementations. Implementations become reviewed artifacts. Decisions that need to survive are preserved as code, documentation, doctrine, or logs.

> **Every watch should leave the ship stronger than it found it.**

## Operating Model

Monad uses a naval command metaphor to make software work easier to reason about and more engaging to operate.

The metaphor is playful, but the underlying process is practical:

- A human operator retains authority over direction and execution.
- AI collaborators can take on planning, implementation, review, documentation, and analysis roles.
- Work is passed between roles through explicit engineering packets rather than vague conversational handoffs.
- Important decisions are written down.
- The repository remains the source of truth.

The project is both a software experiment and an investigation into engineering methodology for the agentic era.

## Current Repository

The repository currently contains experiments in:

- Stateful AI agents
- Operational logging
- Engineering doctrine
- Durable project memory
- AI-assisted software engineering workflows
- Small standalone web experiments ("web toys")

The codebase is evolving from individual prototypes into a collection of reusable engineering instruments.

## Repository Layout

The structure is intentionally evolving as Monad grows.

Representative areas include:

- `docs/` — doctrine, architecture, engineering notes, and watch logs.
- `logs/` — operational records organized by role and watch.
- `toys/` — standalone browser experiments and interface prototypes.
- `projects/` — larger self-contained development efforts.
- Python utilities and agent experiments.

## Philosophy

Monad is guided by a few durable principles:

1. **Human command remains explicit.**
   AI assistance does not erase human responsibility.

2. **Artifacts outrank conversation.**
   Important work must survive outside the chat that produced it.

3. **Memory should be inspectable.**
   A future engineer—or AI—should be able to understand why decisions were made.

4. **Small working systems beat grand descriptions.**
   Progress is measured by running software.

5. **Process is part of the product.**
   Monad studies how software can be built in the agentic era as much as it studies what software to build.

## Current Status

Monad is an active research and prototyping project.

Current work focuses on:

- AI engineering workflows
- Durable operational memory
- Engineering packet methodology
- Human/AI collaboration patterns
- Browser-based operational interfaces
- Development tooling

The long-term objective is a practical development environment where humans and AI collaborate through durable artifacts rather than ephemeral conversations.

## Contributing

The engineering process is still evolving, but thoughtful discussion, experiments, and small, well-documented improvements are welcome.

Preference is given to:

- Simple designs
- Clear documentation
- Small reviewable changes
- Working software
- Durable engineering artifacts

## License

License to be determined.﻿# Monad
# Monad

**Monad is a human-directed software engineering organization built around durable artifacts, persistent operational memory, and AI-assisted development.**

Monad is not a single AI agent or a collection of scripts. It is an engineering methodology for building software through disciplined collaboration between humans and AI.

Ideas become engineering packets. Engineering packets become implementations. Implementations become reviewed artifacts. Every decision expected to survive a watch is preserved as code, doctrine, or operational logs under version control.

The human operator retains command. AI officers contribute planning, implementation, review, documentation, and analysis. The objective is not autonomous software development—it is a repeatable engineering process that becomes more capable, more observable, and easier to continue with every watch.

> **Every watch leaves the ship stronger than it found it.**

The Git repository is the operational memory of Monad. Conversations are working memory; repository artifacts are the authoritative engineering record. A new captain should be able to come aboard, read the logbook, and understand not only what the ship is, but why it became that way.

## Purpose
This repo currently contains:

- A baseline Gemini chat loop.
- Stateful agent experiments that ask the model to return structured JSON.
- A Helmsman variant that writes append-only runtime events to a local log file.
- Documentation for logging doctrine and early project/watch notes.
- Operational logs organized under `logs/`.

Anything beyond those files is TBD.

## Repository Layout

```text
monad/
├── .gitignore
├── README.md
├── agent_v2.py
├── agent_v3.py
├── chat.py
├── helmsman_v2.py
├── helmsman_v2.log
├── docs/
│   ├── logging-doctrine.md
│   └── logs/
│       └── 2026-07-05-morning-watch.md
├── logs/
│   ├── admirals/
│   ├── agents/
│   ├── captains/
│   └── logs/
└── __pycache__/
```

### Top-Level Scripts

- `chat.py` - Baseline interactive chat loop using `gemini-2.5-flash` through the Google GenAI SDK.
- `agent_v2.py` - Stateful interactive agent experiment. It asks the model to return JSON containing `internal_monologue`, `state_updates`, and `response`.
- `agent_v3.py` - Autonomous agent experiment named `Eon`. It maintains in-memory interests/diary state and includes a background loop that uses Google Search grounding.
- `helmsman_v2.py` - Stateful agent variant with an append-only JSONL-style logger that writes runtime events to `helmsman_v2.log`.

### Documentation and Logs

- `docs/logging-doctrine.md` - Defines logging principles and the intended log directory architecture.
- `docs/logs/2026-07-05-morning-watch.md` - Early project/watch note describing Monad as a long-lived engineering program and recording initial architectural decisions.
- `logs/` - Operational log area organized by role/entity and year.

## Setup

TBD: There is no `requirements.txt`, `pyproject.toml`, or other dependency manifest in the repo yet.

The Python scripts currently import the Google GenAI SDK:

```python
from google import genai
from google.genai import types
```

They also expect a `GEMINI_API_KEY` environment variable to be set before running.

Example in Git Bash or another POSIX-style shell:

```bash
export GEMINI_API_KEY="your_key_here"
```

Example in PowerShell:

```powershell
$env:GEMINI_API_KEY = "your_key_here"
```

Dependency installation is TBD until the project adds a dependency manifest. Based on imports, the Google GenAI Python SDK is required.

## Running

From the repository root, run one of the scripts with Python:

```bash
python chat.py
```

```bash
python agent_v2.py
```

```bash
python agent_v3.py
```

```bash
python helmsman_v2.py
```

Known behavior from the files:

- `chat.py`, `agent_v2.py`, and `helmsman_v2.py` are interactive terminal loops.
- `agent_v3.py` starts an interactive loop and also creates a background task for idle activity.
- `helmsman_v2.py` appends runtime events to `helmsman_v2.log`.

TBD: Supported Python version, virtual environment workflow, and exact dependency installation command.

## Current Status

This is an early-stage local agent repository. The project has working Python scripts and initial doctrine/logging documents, but it does not yet have a formal package structure, dependency manifest, test suite, or README-driven onboarding flow beyond this file.

Current repo notes:

- `.gitignore` ignores `.venv/` and `*.env`.
- `helmsman_v2.log` exists as a runtime log at the repository root.
- `__pycache__/` exists as generated Python cache output.
- Qdrant is mentioned in the logging doctrine as a disposable vector/search index concept, but no Qdrant implementation files are present in this repo snapshot.

## Next Steps / TODO

- Add a dependency manifest, such as `requirements.txt` or `pyproject.toml`.
- Document the supported Python version.
- Decide whether runtime logs like `helmsman_v2.log` should remain at the repo root or move under `logs/` according to the logging doctrine.
- Decide whether generated files such as `__pycache__/` should be ignored.
- Add minimal smoke-test or validation instructions.
- Clarify which script is the primary entry point.
- Expand docs as the agent architecture becomes more settled.
