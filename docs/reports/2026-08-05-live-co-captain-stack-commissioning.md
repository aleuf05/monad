# Live Co-Captain Stack Commissioning — 2026-08-05

**Result:** PASS

The Admiral ordered the Co-Captain to manage the active-pair process, kick it
into useful shape, monitor it actively, and find the correct launch sequence.

## Discovery

An initial `systemctl --user` check falsely reported both Captain services
inactive. Inspection established that Monad installs them as system units.
All three required services were healthy, but their unit files encoded only a
network dependency; there was no first-class Captain stack or single verified
launch operation.

## Implemented topology

```text
network-online
  -> public-root-auth.service
  -> live-captain-stack.target
       |- root-console.service :4792
       `- live-captain-bootstrap.service :4778
```

The application services remain parallel peers and share the target lifecycle.
Both declare the auth service as a wanted predecessor and become part of the
stack target.

`live-captain-stack {start|restart|status}` is installed as the operational
command. It verifies system-unit state, waits for actual socket readiness, and
accepts the bootstrap status endpoint's intentional unauthenticated `401` as a
healthy protected boundary.

## Commissioning repairs

1. The first verifier incorrectly used `curl --fail` against the protected
   status endpoint. It was repaired to accept only HTTP 200 or 401.
2. The first restart check raced service activation before socket bind. It was
   repaired with bounded readiness polling before reporting READY.

## Live proof

- `live-captain-stack restart` returned `LIVE CO-CAPTAIN STACK: READY`.
- The target and all three units reported active.
- Ports 4778, 4779, and 4792 were listening on loopback.
- `live-captain-stack.target` is enabled for `multi-user.target`.

This is the first machine-level active-pair process refinement: monitoring now
tests the operational body instead of mistaking service-manager scope or early
process activation for live readiness.
