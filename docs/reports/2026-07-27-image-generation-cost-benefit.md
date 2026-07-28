# Image Generation for Monad — Cost/Benefit Finding

**Date:** 2026-07-27  
**Requested by:** Lieutenant cgl  
**Status:** Technical finding and Captain recommendation  

## Constraint

**Direct human ruling:** The Lieutenant pays $20 per month for ChatGPT Plus and
wants image generation to use that subscription only, with no additional API
spending.

## Verified billing distinction

**Technical finding:** OpenAI documents ChatGPT Plus as a $20-per-month
subscription that includes expanded image-generation access, subject to usage
limits.

**Technical finding:** OpenAI documents ChatGPT and the API platform as
separate billing systems. A ChatGPT Plus subscription does not include API
usage.

Sources:

- <https://help.openai.com/en/articles/6950777-chatgpt-plus>
- <https://help.openai.com/en/articles/9039756-managing-billing-settings-on-chatgpt-web-and-platform>

## Options

### A. Direct OpenAI Image API integration

Benefits:

- deterministic programmatic download;
- provenance fields such as request ID and model;
- straightforward future automation.

Costs and risks:

- billed separately from ChatGPT Plus;
- requires API-key handling;
- may require API organization verification;
- adds an external spending and credential surface;
- violates the Lieutenant's current no-extra-spend constraint.

**Conclusion:** Reject for the current demonstration.

### B. ChatGPT/Codex image generation with reviewed installation

Workflow:

1. The Lieutenant requests an image in the active conversation.
2. The available image-generation tool creates the image under the
   subscription/product entitlement governing that surface.
3. The Lieutenant reviews and approves the result.
4. The approved file is transferred into the repository.
5. The Captain records prompt, date, provenance available from the interface,
   and file hash.
6. After production authorization, the Captain installs it under `web/`, adds
   a visible homepage link, and verifies the public URL.

Benefits:

- no intentional API charge;
- uses the image capability already included with ChatGPT Plus;
- preserves natural conversational prompting;
- keeps a human review gate before publication;
- avoids storing an API key in Monad.

Tradeoffs:

- less automatable than the API;
- transfer from chat output to repository may require an explicit download or
  attachment step depending on the active product surface;
- subscription usage limits still apply;
- the repository cannot independently reproduce the exact image from the
  prompt alone.

**Conclusion:** Best fit under the current constraint.

### C. Local open-source image model on Granite

Potential benefit:

- no per-image OpenAI charge after setup.

Costs and risks:

- substantial model download, storage, GPU/CPU, maintenance, and quality costs;
- unknown Granite hardware suitability;
- distracts from the 24-hour living-archive objective.

**Conclusion:** Not justified for this demonstration.

## Recommendation

**Captain recommendation:** Use option B. Do not configure API billing or run
the prepared API generator. Generate a single reviewed image through the
image-generation capability exposed in this conversation, then perform a
separately authorized static-asset installation into Monad.

## Accuracy boundary

**Unknown:** This repository cannot inspect the Lieutenant's ChatGPT account,
remaining image limits, or product-specific entitlement accounting.

**Technical clarification:** The active conversation exposes an image
generation capability, but no claim should be made about a specific charge
until the governing account interface confirms it. Avoiding the API prevents
intentional API usage charges; it does not redefine subscription limits or
billing policy.
