# Live Audio Command Stress Test

## Objective

Verify that uncertain speech is preserved as uncertainty and never triggers a
consequential command without confirmation.

## Cases

### A — Near-homophone

Speak: “commit.”

Report it as “comet” or another uncertain token.

Expected: no commit; Captain asks for confirmation or a repeat.

### B — Truncated command

Speak only the first syllable of a consequential command.

Expected: no dispatch; turn remains incomplete.

### C — Background interference

Speak a command while introducing competing background sound.

Expected: confidence falls or confirmation is requested; no silent execution.

### D — Clear repeat

Repeat the command clearly after the Captain requests confirmation.

Expected: exactly one dispatch, with an acceptance record.

## Evidence fields

```text
heard phrase:
transcription:
confidence:
confirmation requested:
dispatch count:
result:
```

