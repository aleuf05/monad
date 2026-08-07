# Live Audio Command Safety

An audio token that sounds like a command is not an executed command until it
is intelligible or explicitly confirmed.

## Rule

```text
heard token → transcribe with uncertainty → confirm meaning → execute once
```

If the Admiral reports that “commit” sounded like “comet,” the Captain must:

1. preserve both the likely token and the heard alternative;
2. mark command-word intelligibility as unconfirmed;
3. perform no commit, push, purchase, deletion, or other consequential action;
4. ask for a repeat or explicit confirmation when the command matters.

This protects the Admiral from speech-recognition drift while keeping ordinary
conversation fluid.

