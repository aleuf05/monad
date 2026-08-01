# Root Console Image Preview 0.1

## 1. Originating intent

On 2026-08-01 the Lieutenant asked for a sweet, dynamic popup image previewer in the current conversational surface so visual work can be inspected without leaving the live exchange.

## 2. Verified starting state

- `console/index.html` is the current Root Console page served at `/root/`.
- `console/assets/js/root-console.js` renders Captain messages and Codex protocol items as plain text or activity summaries.
- The retired `console/app.html` redirects away, and its older image-card implementation is not the active surface.
- The working tree already contained unrelated, uncommitted changes, including the current Root Console implementation; those changes were preserved.

## 3. Objective / problem

Make image artifacts visible inside the live Captain conversation and let the operator expand them into a focused inspection stage.

## 4. Scope and exclusions

In scope:

- Recognize image artifacts in completed Captain messages and completed protocol items.
- Render an inline image card in the dialogue column.
- Open a full-screen preview with original-image access, actual-size toggle, backdrop close, and Escape close.
- Respect reduced-motion preference and keyboard focus.

Excluded:

- Changes to image generation, storage, daemon protocol, authentication, or deployment configuration.
- Gallery persistence across page reloads.
- Modification of the live-status column.

## 5. Constraints / authority

- Authorized by the Lieutenant's direct request.
- Repository-local, reversible frontend change only.
- Preserve the existing dialogue/status separation and all unrelated working-tree changes.

## 6. Acceptance criteria

1. A supported image URL or image-generation payload produces an inline preview card.
2. Activating the card opens a modal inspection stage.
3. Escape, the close control, and the empty canvas backdrop close the stage.
4. The stage exposes the original URL and toggles fitted/actual-size inspection.
5. JavaScript parses successfully and the edited files have no whitespace errors.

## 7. Tests / rollback

Tests:

- `node --check console/assets/js/root-console.js`
- `git diff --check -- console/index.html console/assets/js/root-console.js`
- Headless Chromium visual capture was attempted but the host Snap launcher failed while waiting for system profiles; visual human acceptance remains appropriate.

Rollback:

- Revert only the image-preview CSS and stage markup in `console/index.html`, plus the artifact extraction/stage functions and `item/completed` hooks in `console/assets/js/root-console.js`.

## 8. Assigned actor

Codex Captain (`/root`).

## 9. Evidence and completion state

State: **verification pending**.

Evidence:

- Implementation: `console/index.html`
- Behavior: `console/assets/js/root-console.js`
- Static validation commands above passed.
- Visual browser verification is pending because the available Chromium launcher failed before opening the page.

