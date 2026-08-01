"""CLI for a small Nexus harness run."""
import argparse
import json

from .nexus import NexusHarness
from .sweep_controller import SweepDirection, SweepRate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--direction", choices=[item.value for item in SweepDirection], default="FORWARD")
    parser.add_argument("--rate", choices=[item.value for item in SweepRate], default="FAST")
    parser.add_argument("--points", type=int, default=11)
    parser.add_argument("--ticks-per-step", type=int, default=1)
    args = parser.parse_args()
    run = NexusHarness(points=args.points, rate=SweepRate(args.rate), ticks_per_step=args.ticks_per_step).run(seed=args.seed, direction=SweepDirection(args.direction))
    print(json.dumps({"manifest": run.manifest, "replay_digest": run.replay_digest, "events": len(run.events)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
