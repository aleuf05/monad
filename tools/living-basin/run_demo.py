#!/usr/bin/env python3
"""Runs the deterministic acceptance scenario and writes viewer data files.

Usage:
    python3 run_demo.py

Writes into data/:
    world_init.json   seed, grid size, static elevation layer, run metadata
    snapshots.json     periodic full-grid snapshots for scrubbing playback
    events.jsonl        the complete, ordered causal event log
    features.json         the final feature registry
    checksum.txt          final-state checksum + summary counts (for humans
                           and for the replay test to compare against)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from scenario import build_simulation, DEMO_SEED, DEMO_TICKS, SNAPSHOT_INTERVAL  # noqa: E402

DATA_DIR = HERE / "data"


def main() -> None:
    sim = build_simulation()

    snapshots = [{"tick": 0, "layers": sim.world.snapshot()}]
    for t in range(1, DEMO_TICKS + 1):
        sim.tick()
        if t % SNAPSHOT_INTERVAL == 0 or t == DEMO_TICKS:
            snapshots.append({"tick": t, "layers": sim.world.snapshot()})

    DATA_DIR.mkdir(exist_ok=True)

    world_init = {
        "seed": DEMO_SEED,
        "grid_size": sim.world.n,
        "total_ticks": DEMO_TICKS,
        "snapshot_interval": SNAPSHOT_INTERVAL,
        "elevation": [[round(v, 4) for v in row] for row in sim.world.fields["elevation"]],
        "herbivore_count": len(sim.herds),
    }
    (DATA_DIR / "world_init.json").write_text(json.dumps(world_init))
    (DATA_DIR / "snapshots.json").write_text(json.dumps(snapshots))
    (DATA_DIR / "events.jsonl").write_text(sim.event_log.to_jsonl())
    (DATA_DIR / "features.json").write_text(json.dumps(sim.features.to_dict(), indent=1))

    by_type: dict[str, int] = {}
    for f in sim.features.all():
        by_type[f.feature_type] = by_type.get(f.feature_type, 0) + 1

    summary = (
        f"seed={DEMO_SEED} ticks={DEMO_TICKS}\n"
        f"checksum={sim.checksum()}\n"
        f"events={len(sim.event_log)}\n"
        f"features={dict(sorted(by_type.items()))}\n"
        f"lineage_acyclic={sim.event_log.is_acyclic()}\n"
    )
    (DATA_DIR / "checksum.txt").write_text(summary)
    print(summary)
    print(f"wrote {DATA_DIR}")


if __name__ == "__main__":
    main()
