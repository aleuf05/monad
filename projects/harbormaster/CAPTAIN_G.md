# Mission

Prepare and execute Harbormaster with discipline.

This project exists to create a useful operational artifact, not to impress anyone with machinery.

# Commander Intent

Gemini CLI should be able to enter this directory, read `GEMINI_TASK.md`, and begin work without needing chat history as hidden context.

The implementation should serve Lieutenant cgl's actual workflow. Prefer direct usefulness over completeness.

# Implementation Philosophy

Prefer simple solutions.

Avoid unnecessary dependencies.

Do not gold-plate.

Keep the implementation maintainable.

If uncertain, choose the simpler implementation and write down the assumption.

Keep state visible. Keep behavior inspectable. Keep failure modes understandable.

# What Success Looks Like

Harbormaster does one clear job well.

Lieutenant cgl can run it locally without ceremony.

The repository explains what exists, how to run it, and what remains unfinished.

The watch leaves behind artifacts that a later officer can read without asking what happened in chat.

# When To Stop

Stop when the accepted sprint objective is satisfied.

Stop before adding secondary features.

Stop before adding dependencies that are merely convenient.

Stop and report if the task requires touching production systems, secrets, unrelated Monad components, or architecture outside `projects/harbormaster/`.
