# MIKE-ROCKETRY-GLB-INTAKE-0.1

## 1. Originating intent

The Admiral ordered the Tripo helper page to accept the returned GLB directly,
with phone ease as the governing interaction requirement.

## 2. Verified starting state

The static helper could download/share the source and open Tripo. Returning a
GLB required moving it manually to Granite. The existing asset-viewer endpoint
is loopback-only and also accepts images that trigger billed Replicate work, so
it is unsuitable for public exposure.

## 3. Objective / problem

Add a narrow public GLB-only quarantine intake and a phone upload form.

## 4. Scope and exclusions

Accept one multipart `.glb` up to 30 MB; validate GLB v2 structure and nonempty
mesh primitives; store bytes plus receipt under `data/mike-rocketry-intake/`;
require Captain review. Exclude images, provider calls, automatic cataloging,
automatic publication, and runtime use.

## 5. Constraints / authority

No paid generation path may be exposed. Caddy and systemd commissioning must
use `cmd.sh`. Uploaded content remains untrusted and quarantined.

## 6. Acceptance criteria

- Phone can choose and submit a GLB from the helper.
- Invalid/non-GLB/empty assets are rejected.
- Valid assets receive hash, size, mesh count, stored name, and review status.
- No upload is automatically served or entered into the asset manifest.
- Public route works only after explicit operator commissioning.

## 7. Tests / rollback

Unit-test validator; loopback smoke-test valid and invalid multipart uploads;
test phone UI success/failure states; then commission and verify public route.
Rollback disables/removes service and Caddy route and reverts the UI.

## 8. Assigned actor

Captain implements; operator executes the pinned privileged commissioning
handoff.

## 9. Evidence and completion state

**Lifecycle:** executing; commissioning pending.

Pre-commissioning evidence:

- three GLB validator unit tests pass;
- loopback health returns service identity and 30 MB limit;
- valid multipart GLB receives HTTP 201, SHA-256, mesh/primitive counts, unique
  stored name, and `quarantined-review-required`;
- non-GLB upload receives HTTP 400;
- smoke-test intake files were moved out of the repository after validation;
- Caddy route and systemd unit are staged but not installed.
