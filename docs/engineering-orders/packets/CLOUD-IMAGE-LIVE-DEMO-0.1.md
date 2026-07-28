# CLOUD-IMAGE-LIVE-DEMO-0.1

## 1. Originating intent

The Lieutenant requested a demonstration in which an image derived from the
current conversation is generated in the cloud, downloaded, and installed
visibly into the running Monad system.

## 2. Verified starting state

- `web/` is documented as Granite's live Caddy web root.
- `https://cameronlampley.com/` is the documented public entrance.
- The homepage already links PNG artifacts under `web/assets/`.
- No `.openai/hosting.json` was found in or above the repository.
- No existing OpenAI image-generation code was found in the searched project
  paths.
- Existing uncommitted changes are present and must be preserved.
- A production freeze is active under the current Admiral/Captain context.

## 3. Objective / problem

Demonstrate a provenance-preserving path from conversational intent to a
cloud-generated image and then, after explicit authorization, to a
click-reachable live Monad artifact.

## 4. Scope and exclusions

In scope:

- one original PNG;
- one prompt record;
- one private generation sidecar;
- one public-safe provenance record;
- one homepage card;
- verification against the real site.

Excluded:

- autonomous recurring generation;
- browser-side API calls;
- exposing an API key;
- new services, ports, Caddy routes, containers, or databases;
- changes to Granite access, SSH, Portainer, or Qdrant;
- claims that image generation proves conversation persistence or canon.

## 5. Constraints / authority

- The Image API call may incur cost and requires an authorized API key.
- Secret contents must not be printed or committed.
- Production installation requires explicit approval after image review.
- `web/index.html` is the source; `web/command-deck.html` must be regenerated.
- The current production freeze must be lifted or specifically excepted before
  modifying `web/`.

## 6. Acceptance criteria

- The cloud API returns an image derived from the recorded prompt.
- The image is decoded to a PNG outside `web/` first.
- SHA-256, model, prompt path, timestamp, and request ID are recorded privately.
- The Lieutenant reviews the generated image before publication.
- The approved PNG is visible through a direct HTTPS URL.
- A `NEW` homepage card makes it click-reachable from the site root.
- The public page and image return successful responses and match expected
  content after installation.
- No secret appears in Git, HTML, logs, or provenance files.

## 7. Tests / rollback

Tests:

- `python3 -m py_compile tools/cloud-image-demo/generate_image.py`
- generator refuses a `web/` output without `--allow-live-target`;
- inspect file type, dimensions, and SHA-256;
- `python3 tools/sync-command-deck.py`;
- fetch the public homepage and image URL;
- confirm the new card and image visually.

Rollback:

- remove the new homepage card;
- regenerate `web/command-deck.html`;
- move the generated public asset and provenance record out of `web/`;
- verify the public URLs no longer expose the demonstration.

Rollback must preserve the private generation artifact and packet evidence.

## 8. Assigned actor

Captain / Commander Codex, under the Lieutenant's explicit production
authorization.

## 9. Evidence and completion state

**Lifecycle:** blocked

**Blocker:** The Lieutenant requires that the demonstration use the existing
ChatGPT Plus subscription without additional spending. OpenAI API usage is
billed separately from ChatGPT, so the API-based execution path is outside the
authorized cost boundary.

**Recommended replacement:** Generate the image through the image-generation
capability exposed in the active ChatGPT/Codex conversation, review it, transfer
the approved artifact into the repository, then continue with the packet's
provenance, homepage-installation, and live-verification steps without an API
call.

Prepared:

- `tools/cloud-image-demo/generate_image.py`
- `tools/cloud-image-demo/monad-actual.prompt.txt`
- `tools/cloud-image-demo/README.md`

Not yet performed:

- API credential verification;
- billable cloud generation;
- image review;
- any write under `web/`;
- live URL verification.

No claim of cloud generation, download, installation, deployment, or live
success has been made.
