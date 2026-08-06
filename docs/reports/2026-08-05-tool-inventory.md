# Tool Inventory — what is running, what is wired, what is orphaned

Date: 2026-08-05
Task: `TOOL-INVENTORY-01`
Method: systemd `ExecStart` scan across `/etc/systemd/system/*.service` and
`scripts/*.service`, then reference search across `.py`, `.html`, `.js`,
`.sh`, `.service`, excluding each directory's own files, `node_modules`,
`.venv`, `docs/`, and `logs/`.

**Nothing was deleted. The deliverable is the list.**

---

## The headline number was wrong, and I was the one repeating it

This inventory was queued on the premise "36 tool directories, 7 running
services." That framing appears in the chief plan, in doctrine 016's
worked example, and in the Living Semantic World Engine draft. **It
overstated the gap.**

Actual count:

| | Count |
|---|---|
| Tool directories | 35 (36 minus `__pycache__`) |
| **Active systemd units** | **15** |
| Distinct tool dirs with an active unit | **12** |
| Dirs wired to something that runs | 19 |
| **True orphans** | **4** |

"Seven services" came from `OPERATION-RESUME`'s table, which lists the
seven the Operation was *working on* — not the total running on the host.
Six units were never in that table: `living-captain-status`,
`living-captain-workbench`, `living-fleet`, `living-fleet-memory`,
`mike-rocketry-glb-intake`, `public-images-api`, `world-intake`,
`gasket-upload`.

The circulation argument in
`docs/research/LIVING_SEMANTIC_WORLD_ENGINE_DRAFT_2026-08-05.md` §6 cites
the wrong ratio. The diagnosis survives — 4 orphans and 16 dirs with no
unit is still weak circulation — but it is **35 → 12, not 36 → 7**, and the
draft should be read with that correction.

---

## Running — an active systemd unit executes it (12 dirs, 15 units)

| Directory | Unit(s) |
|---|---|
| `aegis-inspect` | `aegis-inspect` |
| `docx-intake` | `docx-intake` |
| `gasket-upload` | `gasket-upload` |
| `live-captain` | `live-captain-bootstrap` |
| `living-captain` | `live-captain-web`, `living-captain-status` |
| `living-captain-workbench` | `living-captain-workbench` |
| `living-fleet` | `living-fleet`, `living-fleet-memory` |
| `m3-cycle` | `m3-cycle` |
| `mike-rocketry` | `mike-rocketry-glb-intake` |
| `public-root-auth` | `public-root-auth` |
| `root-console` | `root-console`, `public-images-api` |
| `world-intake` | `world-intake` |

**Installed but not active** — units exist, currently down:

- `chat-captain-web` → `chat-captain` (inactive, **disabled**; consistent
  with `current-bearing.md`, which records the legacy Chat Captain as
  deliberately parked and preserved)
- `public-docs-api` → `root-console` (inactive, disabled)
- `living-fleet-memory-reflect` → `living-fleet` (`static` — a one-shot,
  not a failure)

## Wired — imported or invoked by something that runs (7 more dirs)

`aegis-rig`, `agent-registry`, `context-steward`, `engineering-comms`,
`img2asset`, `kraken-watch`, `legend-pipeline`, `libfive`, `living-basin`,
`mission-bus`, `mission-director`, `monad0`, `npr-fetch`, `npr-headlines`,
`npr-podcasts`, `review-inbox`, `voice-engine`, `watch-officer`.

## Orphans — no unit, no importer (4)

| Directory | Last touched | Note |
|---|---|---|
| `beastscape-umap` | 2026-07-31 | Beast latent-space work; the research draft it belongs to is filed, the tool is unreferenced |
| `phone-image-intake` | 2026-07-28 | Committed in the same commit as `cloud-image-demo` |
| `cloud-image-demo` | 2026-07-28 | Only self-references |
| `radio-traffic-eval` | 2026-07-16 | JavaScript, no Python; zero references anywhere |

Four orphans out of thirty-five is a **healthier repository than the
premise assumed.** Three of the four are recent experiments rather than rot,
and `radio-traffic-eval` passed 11/11 when it landed.

---

## Method note: the first pass was wrong, and how

The initial classification searched for the literal string `tools/<dir>` and
the underscored module name. It reported **`aegis-rig` as an orphan** — a
directory built earlier the same day whose solver and pipeline are imported
by `aegis-inspect/server.py`, which is running right now.

The miss: that import goes through `sys.path.insert(...)` plus a bare
`import pipeline`, so neither `tools/aegis-rig` nor `aegis_rig` appears
anywhere. Any inventory of this repo that greps for directory paths will
produce false orphans, because `sys.path` manipulation is the normal import
idiom here.

The corrected pass enumerates each directory's module names and searches for
`import <module>` / `from <module>`. That is what the numbers above use.

**Consequence for anyone repeating this:** an automated orphan check would
have recommended deleting live code. Verify every orphan by module name
before acting on it. This is also why the task said delete nothing.

---

## What this changes

1. **Correct the ratio** wherever it is quoted — chief plan §3, doctrine
   016 §5, and the Living Semantic World Engine draft §6.
2. **The "weak circulation" diagnosis stands but is weaker than argued.**
   16 of 35 directories have no unit, and only 4 are genuinely unreferenced.
   The repo is better connected than the premise claimed.
3. **`engineering-comms` is no longer the flagship example.** It is now
   wired — `mission_bus.py` picked it up. The comment recording that it once
   sat unused is history, not current state.
4. **No deletions recommended.** The four orphans cost nothing to keep, and
   the false-orphan finding above is reason enough to be slow here.
