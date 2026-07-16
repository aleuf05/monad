# Model API routing

Date established: 2026-07-16
Authority: Lieutenant

All live generative-model API calls in Monad route through Gemini. New work
must not require, request, or block on OpenAI or Anthropic credentials.
Multi-role and multi-agent features may make multiple Gemini calls; they do
not require multiple model vendors.

Provider-neutral internal interfaces may remain where they keep component
boundaries clean, but Gemini is the only commissioned external model provider.
References to other providers in historical reports describe their state at
the time and are not active provisioning requirements.

API keys remain runtime/operator inputs and must not be committed to git.

This ruling resolves `HEART-01`; its obsolete credential request was removed
from the work queue when this doctrine was recorded.
