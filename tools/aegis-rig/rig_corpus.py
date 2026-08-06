#!/usr/bin/env python3
"""Run the whole pipeline over every static asset in the corpus.

AUTHORIZE, EXECUTE, then probe the result. Prints a table and writes
`web/data/corpus-rig.json` for the front page. Does not commit — RECORD is
per-asset and deliberately a separate decision.

Bone count is chosen per asset rather than fixed: the fragmentation scale
bounds how dense a chain is useful, so a heavily fragmented mesh gets more
joints than a coherent one before every shell goes rigid.
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "aegis-inspect"))
import deform  # noqa: E402
import inspector  # noqa: E402
import pipeline  # noqa: E402
import solver  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_JOINTS = 8


def run(joints: int = DEFAULT_JOINTS, probe_angles=(15.0, 45.0)) -> dict:
    corpus = inspector.collect(REPO_ROOT)
    results = []

    for asset in corpus["assets"]:
        if not asset.get("ok") or asset.get("state") != "static":
            continue
        source = REPO_ROOT / asset["path"]
        row = {"asset": asset["name"], "path": asset["path"],
               "vertices": asset["vertices"], "bytes": asset["bytes"]}

        started = time.perf_counter()
        try:
            auth = pipeline.authorize(source, joints)
            row["gates"] = [{"gate": g["gate"], "passed": g["passed"],
                             "detail": g["detail"]} for g in auth["gates"]]
            if not auth["ok"]:
                row.update({"status": "refused", "note": auth["note"]})
                results.append(row)
                continue

            # shape="auto" lets the fit gate choose chain or tree per asset,
            # and keeps the tree only when it actually scores better.
            report = solver.write_rigged(
                REPO_ROOT / auth["source"], REPO_ROOT / auth["dest"],
                joints, shape="auto")
            report.update({"source": auth["source"], "dest": auth["dest"]})
            row.update({
                "status": "rigged",
                "dest": report["dest"],
                "joints": report["joint_count"],
                "shells": report["shells"],
                "rigid_shells": report["rigid_shells"],
                "blended_shells": report["blended_shells"],
                "rigged_bytes": report["rigged_bytes"],
                "solve_ms": report["solve_ms"],
                "engine": report["engine"],
                "skeleton_kind": report.get("skeleton_kind", "chain"),
                "max_weight_error": report["max_weight_error"],
            })

            probe = deform.probe(REPO_ROOT / report["dest"], probe_angles)
            row["probe"] = {
                "verdict": probe["verdict"],
                "note": probe["note"],
                "poses": [{k: p[k] for k in
                           ("degrees", "verdict", "inverted", "collapsed",
                            "torn", "clipping_pairs", "deep_clipping",
                            "max_stretch", "hotspots")}
                          for p in probe["poses"]],
            }
        except Exception as error:  # noqa: BLE001 - one bad asset must not stop the run
            row.update({"status": "error", "note": str(error),
                        "trace": traceback.format_exc(limit=2)})
        row["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 1)
        results.append(row)

    rigged = [r for r in results if r["status"] == "rigged"]
    return {
        "generated": time.strftime("%Y-%m-%d"),
        "joints_requested": joints,
        "attempted": len(results),
        "rigged": len(rigged),
        "refused": sum(1 for r in results if r["status"] == "refused"),
        "errors": sum(1 for r in results if r["status"] == "error"),
        "total_vertices": sum(r["vertices"] for r in rigged),
        "assets": results,
    }


def main(argv: list[str]) -> int:
    joints = int(argv[1]) if len(argv) > 1 else DEFAULT_JOINTS
    summary = run(joints)

    print(f"{'asset':<38} {'verts':>10} {'status':<9} {'shells':>7} "
          f"{'rigid':>6} {'blend':>6} {'ms':>7}  probe")
    print("-" * 108)
    for row in summary["assets"]:
        probe = row.get("probe", {})
        print(f"{row['asset'][:37]:<38} {row['vertices']:>10,} "
              f"{row['status']:<9} {row.get('shells', 0):>7,} "
              f"{row.get('rigid_shells', 0):>6,} {row.get('blended_shells', 0):>6,} "
              f"{row.get('solve_ms', 0):>7.1f}  "
              f"{probe.get('verdict', row.get('note', ''))[:40]}")
    print("-" * 108)
    print(f"{summary['rigged']} rigged, {summary['refused']} refused, "
          f"{summary['errors']} errors, {summary['total_vertices']:,} vertices")

    out = REPO_ROOT / "web/data/corpus-rig.json"
    out.write_text(json.dumps(summary, indent=2))
    print(f"wrote {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
