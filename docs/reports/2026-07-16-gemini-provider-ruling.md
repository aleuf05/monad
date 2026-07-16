# Gemini provider ruling

The Lieutenant ruled on 2026-07-16 that all Monad model API calls use Gemini.
OpenAI and Anthropic keys are not dependencies for the Heart of Monad or later
component glue.

Evidence at closure:

- the live Cognition Graph already stores a Gemini key locally in the
  operator's browser and calls the Gemini API;
- the homepage's stale Anthropic-key instruction was corrected to Gemini;
- `HEART-01`, which requested credentials for two different vendors, was
  removed from the active work queue;
- the durable routing rule now lives in
  `docs/doctrine/model-api-routing.md`.

No credential value was added to the repository.
