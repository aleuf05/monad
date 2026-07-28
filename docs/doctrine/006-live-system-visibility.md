# Doctrine 006 — Live-System Visibility

**Authority:** Admiral / Lieutenant cgl  
**Recorded:** 2026-07-27  
**Status:** Active delivery preference, subject to operational approval gates  

## Ruling

**Project doctrine:** Project Monad is intended to be a living system. When
feasible, safe, and authorized, changes to the site should be performed and
verified on the actual running site so their effects are visible in real time.

## Meaning

Live visibility is preferred when:

- the exact production target has been verified;
- the change is small and reversible;
- relevant evidence has been preserved;
- rollback is understood;
- the applicable human approval has been given;
- the result can be observed directly on the real site.

## Boundaries

This doctrine is a delivery preference, not blanket execution authority. It
does not override:

- a production or security freeze;
- explicit approval requirements;
- evidence-preservation duties;
- credential, network, service, or deployment controls;
- the requirement to distinguish local edits from verified live behavior.

**Technical finding:** A repository edit is not proof of public delivery.
Live status must be verified against the actual running system before it is
reported as live.

## Current interaction with repository doctrine

**Technical finding:** Existing repository instructions state that `web/` is
the production target and that edits there may affect the live site directly.

**Project doctrine:** Because production behavior is immediate, verification
and authorization must precede edits under `web/` while a production freeze is
active.
