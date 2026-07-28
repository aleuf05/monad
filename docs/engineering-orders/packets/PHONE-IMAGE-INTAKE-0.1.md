# PHONE-IMAGE-INTAKE-0.1

## 1. Originating intent

The Lieutenant authorized implementation of a semi-automated bridge from
ChatGPT image generation on his phone to Monad on Granite, with minimal human
glue and no separate OpenAI API spending.

## 2. Verified starting state

- The active host reports hostname `granite`.
- Repository root is `/home/cgl/dev/monad`.
- `scp`, `sha256sum`, and `file` are installed on Granite.
- Phone-to-Granite SSH remains unverified in the current session.
- `web/` is the live production root and must not receive unreviewed images.

## 3. Objective / problem

Reduce the human workflow to image generation, download, one Termux command,
review, and a separate publish order.

## 4. Scope and exclusions

In scope:

- select the newest supported phone download;
- transfer it to Granite over SSH;
- validate type and size;
- hash it and create a private provenance sidecar;
- hold it pending human review.

Excluded:

- OpenAI API calls or API keys;
- automatic publication;
- changes to SSH, router, firewall, or credentials;
- writes under `web/`;
- background watchers or daemons.

## 5. Constraints / authority

- The Lieutenant authorized repository implementation.
- Publication remains a separate production action.
- Sensitive metadata and secret contents must not become public.
- Existing repository changes must be preserved.

## 6. Acceptance criteria

- Receiver accepts PNG, JPEG, and WebP by content signature.
- Receiver rejects unsupported content, empty files, and files over 25 MiB.
- Each accepted image receives a SHA-256 and JSON sidecar.
- Intake artifacts remain outside `web/` and ignored by Git.
- Termux uploader selects the newest supported download.
- A local Granite fixture completes the receiver path.
- The real phone transfer remains explicitly unverified until performed.

## 7. Tests / rollback

Tests:

- compile the Python receiver;
- ingest a known repository PNG as a private fixture;
- verify sidecar hash and pending status;
- run shell syntax validation on the Termux uploader.

Rollback:

- remove `tools/phone-image-intake/`;
- remove this packet;
- remove the `data/image-intake/` ignore entry;
- preserve or separately archive any human-approved intake artifacts before
  clearing private runtime data.

## 8. Assigned actor

Captain / Commander Codex.

## 9. Evidence and completion state

**Lifecycle:** executing

Implementation prepared:

- `tools/phone-image-intake/monad-image-push`
- `tools/phone-image-intake/receive_image.py`
- `tools/phone-image-intake/README.md`

Pending:

- local Granite fixture test;
- real phone-to-Granite SSH transfer;
- Lieutenant walkthrough;
- live publication test after review and approval.
