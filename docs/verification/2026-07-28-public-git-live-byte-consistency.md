# Public Git / Live Deployment Byte Consistency

- **Observed:** 2026-07-28
- **Status:** Verified technical finding with declared runtime exceptions
- **Observer:** Codex
- **Public origin:** `git@github.com:aleuf05/monad.git`
- **Live origin:** `https://cameronlampley.com/`

## Result

**Technical finding:** The public deployment tree tracked by Git was reconciled
without a force-push or a change to the live tree. The production branch now
contains the previous public `main` history through a normal merge.

The byte-level verifier covers every Git-tracked regular file under `web/` and
`docs/` that has a public HTTPS representation. It also checks HTTP success,
Git-to-working-tree equality, and working-tree-to-live equality.

## Generated data projection snapshot

Commit `e7d56a9` records a point-in-time snapshot of the four continuously
generated public projections. At capture time, local and live SHA-256 values
were identical:

| Projection | SHA-256 |
|---|---|
| `web/data/fleet-status.json` | `7544982f72a4488b348995061e9852e4fb59f02bebf4cc5311b94bcd4814ade3` |
| `web/data/npr-headlines.json` | `f9117f84e4dc7d8bfa074deac4ccccfb1545a30c131754ea8653d37649fcfec3` |
| `web/data/review-inbox.json` | `5d9c8b7b985f4a185f5ab6ff06de07ebe5c2a4a414785241bf7298145702915f` |
| `web/data/watch-officer-status.json` | `99dde89894226d0bd943377f3189205f627b4f46bcd7768e28767e977ad805f9` |

**Operational limit:** These files are projections produced by live scheduled
jobs. A later successful generator run changes production bytes without making
a Git commit. Therefore a Git snapshot can prove exact equality at an observed
instant, but cannot make equality permanent while both conditions remain true:
the files are continuously generated and their snapshots are tracked in Git.
Future drift in these four named paths is expected runtime behavior and must be
reported as such, not silently counted as source-tree inconsistency.

## Deliberately non-Git runtime assets

Four live GLB files under `web/assets/models/` are deliberately excluded by
`.gitignore`; the repository comment says they live on the serving host and are
regenerated or recopied there. They are public deployment dependencies but are
not Git blobs:

| Runtime asset | SHA-256 |
|---|---|
| `end-to-end-manual.glb` | `9a4662ede659bedbe868c3292d35cc68ef1ac94f5383ee8ed5bab09e6d3e47e5` |
| `file_00000000a68c722f9cd29e1996dba4cf.glb` | `d192727a2f604e4ebb94ff12994ed3c02bfe70e902ec7824e42f44c3dcf504f8` |
| `the-monad.glb` | `0f01262d464e9f4c27ddbf49fda0ee0f1abb95fb3bbb3e7cedf29f4f6d6b51ae` |
| `uss-rubber-ducky.glb` | `9a4662ede659bedbe868c3292d35cc68ef1ac94f5383ee8ed5bab09e6d3e47e5` |

This is a declared content boundary, not byte equality: public Git cannot be
byte-identical to files it intentionally does not contain. Adding roughly
147 MiB of generated binaries merely to erase that declared distinction was
not treated as a safe reconciliation step.

## Symlink treatment

- `web/docs -> ../docs`: tracked documentation is compared to its public
  `/docs/...` HTTPS representation.
- `web/assets/intake/kraken_tripo_v1.glb` points to the tracked
  `assets/intake/kraken_tripo_v1.glb`: the link target's bytes, rather than the
  symlink text, are compared to the public asset response.

## Interpretation

The strongest accurate statement is:

> Public Git and the live deployment are byte-identical for the complete
> Git-governed public surface at the recorded verification instant. Four
> continuously generated JSON projections may drift after their snapshot, and
> four explicitly ignored runtime GLBs remain outside Git by repository design.

No broader claim of permanent whole-host identity is supported.
