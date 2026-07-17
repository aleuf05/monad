#!/usr/bin/env python3
"""Backfill bounding_box/orientation_warnings/version onto manifest.json
entries for GLBs that are already cataloged in place -- distinct from
image_to_asset.py's normal --backend manual flow, which assumes the input
is a separate source file being copied *into* web/assets/models/ (and
refuses to copy a file onto itself). This script never moves or renames
any .glb; it only re-reads what's already there and updates the manifest.

Does not fabricate a real-world scale for anything -- existing entries
keep declared_scale_meters: null, scale_declared_unknown: True (an honest
"we don't know," not a guess) unless --scale is passed for a specific name.

See docs/architecture/golden-hull-asset-validation-v0.1.md.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from image_to_asset import (  # noqa: E402
    ASSETS_DIR,
    MANIFEST_PATH,
    REPO_ROOT,
    check_orientation,
    compute_bounding_box,
    read_gltf_json,
)


def audit_one(entry: dict, scale_overrides: dict[str, float], acknowledge_unknown: bool, log=print) -> dict:
    name = entry["name"]
    glb_path = os.path.join(REPO_ROOT, entry["glb_path"])
    gltf = read_gltf_json(glb_path)
    bounding_box = compute_bounding_box(gltf) if gltf is not None else None
    orientation_warnings = check_orientation(bounding_box) if bounding_box else []
    if bounding_box is None:
        log(f"WARNING: {name} -- could not compute a bounding box.")
    for warning in orientation_warnings:
        log(f"WARNING: {name}: {warning}")

    declared_scale_meters = scale_overrides.get(name, entry.get("declared_scale_meters"))
    scale_declared_unknown = entry.get("scale_declared_unknown", False)
    if declared_scale_meters is not None:
        scale_declared_unknown = False
    elif name in scale_overrides:
        pass  # can't happen: scale_overrides only holds non-None values
    elif acknowledge_unknown:
        scale_declared_unknown = True
    elif not scale_declared_unknown:
        log(f"WARNING: {name} audited with no declared real-world scale on record and not explicitly acknowledged unknown -- pass --scale {name}=METERS or --acknowledge-unknown.")

    updated = dict(entry)
    updated["version"] = entry.get("version", 0) + 1
    updated["bounding_box"] = bounding_box
    updated["orientation_warnings"] = orientation_warnings
    updated["declared_scale_meters"] = declared_scale_meters
    updated["scale_declared_unknown"] = scale_declared_unknown
    updated["audited_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return updated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scale", action="append", default=[], metavar="NAME=METERS",
        help="declare a real-world scale for one already-cataloged model by name, e.g. --scale the-monad.glb=180",
    )
    parser.add_argument(
        "--acknowledge-unknown", action="store_true",
        help="explicitly mark every audited model without a --scale override as scale_declared_unknown=true "
        "(an honest 'we checked and don't know', not silence)",
    )
    parser.add_argument("--dry-run", action="store_true", help="print findings without writing manifest.json")
    args = parser.parse_args()

    scale_overrides = {}
    for item in args.scale:
        if "=" not in item:
            raise SystemExit(f"error: --scale must be NAME=METERS, got {item!r}")
        name, value = item.split("=", 1)
        scale_overrides[name] = float(value)

    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)

    audited = [audit_one(entry, scale_overrides, args.acknowledge_unknown) for entry in manifest.get("models", [])]
    manifest["models"] = audited
    manifest["schema_version"] = "monad.assetManifest.v2"

    if args.dry_run:
        print(json.dumps(manifest, indent=2))
        return

    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")
    print(f"Audited {len(audited)} model(s), wrote {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
