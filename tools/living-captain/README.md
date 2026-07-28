# Project Monad — Live Captain — Version 1

Live Captain is a local terminal conversation component with durable history
and a replaceable inference provider. It is software, not a conscious or
autonomous actor. Version 1 has no shell, tools, background work, public
listener, or authority to modify Monad canon.

## Start

The operator launcher on Granite is:

```text
/home/cgl/captain.sh
```

It loads `GEMINI_API_KEY` from the protected local environment file and then
starts the terminal client. The key is never passed as a command-line
argument.

Inside the client:

- `/status` shows provider and conservative local usage accounting.
- `/quit` shuts down cleanly.
- `Ctrl-C` and end-of-file also shut down cleanly.

## Local state

Runtime state is under `data/living-captain/`, which is ignored by Git:

- `conversation.jsonl`: append-only transcript
- `conversation-state.json`: stable active session identity
- `usage.json`: persistent request, token, and estimated-cost boundary
- `live-captain.log`: metadata-only lifecycle and failure log

The entire transcript stays local. A bounded recent window is selected for
each Gemini request; old entries are not overwritten or replaced by a model
summary.

## Usage boundary

Version 1 permits at most 25 requests, estimates at most 8,000 input tokens
per request, and requests at most 512 output tokens. Before network activity,
it persistently reserves a deliberately conservative cost estimate and
rejects any request that could take that estimate above $2.

This is a local approximation, not provider billing authority. Provider-side
spend controls remain the strongest backstop, and delayed provider accounting
can permit overage.

## Tests

```text
python3 -m unittest discover -s tools/living-captain -p 'test_*.py' -v
```
