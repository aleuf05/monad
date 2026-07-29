# MIKE-ROCKETRY-TRIPO-BRIDGE-0.1

## 1. Originating intent

The Admiral requested 3D rocket assets, selected Tripo as provider, reported
that credits are available but operation remains manual, and asked for a small
website helper to move the image and resulting asset through that process.

## 2. Verified starting state

A reconstruction-ready PNG and Tripo intake contract existed in the portable
local package. The live Mike page exposed neither. Monad's Asset Viewer accepts
manual GLBs, but its uploader intentionally targets a loopback-only service on
port 8501 and is therefore not a universal browser return path.

## 3. Objective / problem

Make the manual handoff obvious: download the prepared source from the live
page, run it through authenticated Tripo, export GLB, and return the local file
path to the Captain for validation.

## 4. Scope and exclusions

Scope: publish the source PNG, visible instructions, a download link, and a
link to the existing Asset Viewer for Granite-local use. Excluded: Tripo API
integration, credential handling, automatic generation, GLB claims, and 3D
integration into Version 1.

## 5. Constraints / authority

Provider is Tripo. Do not substitute Replicate/Hunyuan. Preserve explicit
manual-operation and no-result-yet status.

## 6. Acceptance criteria

- Live helper displays the exact prepared source plate.
- The source downloads with a meaningful filename.
- Instructions name Tripo settings and GLB return step.
- The helper states that no Tripo model has yet been claimed.
- Existing 2D laboratory remains independent of the sidecar.

## 7. Tests / rollback

Verify source hash, HTTP 200, download headers/content, visible helper text,
desktop/mobile rendering, and link targets. Rollback removes the helper,
source image, and packet.

## 8. Assigned actor

Captain / Codex CLI; manual generation assigned to the authenticated human
operator.

## 9. Evidence and completion state

**Lifecycle:** verified complete → recorded.

Prepared source SHA-256:
`3c7e5706b380a2c3c756e5c6c71830056d2a811d7b059ede1e3d10dd467b596a`.

Verified 2026-07-29:

- live PNG: HTTP 200 and exact SHA-256 match;
- live page contains helper title, download action, and explicit
  no-Tripo-model-yet boundary;
- download href targets the exact published PNG;
- Chromium helper rendering at 1440 × 1000 and 390 × 844: visible and within
  viewport bounds;
- existing Asset Viewer link retained as a Granite-local optional return path.
