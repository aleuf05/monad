#!/usr/bin/env python3
"""Image -> 3D asset pipeline for Monad. Contracts-only: this tool never
touches FleetCore or World state, it only reads a source image and
writes a .glb file plus a manifest entry under web/assets/models/ --
live-served directly, no deploy step, see docs/deployment.md.

Usage:
    image_to_asset.py <input.png> --output <name>.glb [--backend hf_spaces|replicate]
    image_to_asset.py <downloaded.glb> --output <name>.glb --backend manual [--source <original-image-path>]

--backend manual exists because ZeroGPU-backed public Spaces (which is
most of them -- checked five, all ZeroGPU) reject gradio_client/API calls
at the actual generation step; only a genuine browser session gets past
their X-IP-token gate. Generate through the Space's own web UI, download
the result, then run this to validate and catalog it -- see
logs/captains/2026 for the investigation that ruled out fixing this in
code.
"""
import argparse
import datetime
import json
import os
import shutil
import sys
import tempfile

from PIL import Image

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ASSETS_DIR = os.path.join(REPO_ROOT, "web", "assets", "models")
MANIFEST_PATH = os.path.join(ASSETS_DIR, "manifest.json")

VALID_INPUT_FORMATS = {"PNG", "JPEG", "WEBP"}


def validate_image(path: str) -> Image.Image:
    if not os.path.isfile(path):
        raise SystemExit(f"error: input image not found: {path}")
    try:
        img = Image.open(path)
        img.load()
    except Exception as exc:
        raise SystemExit(f"error: could not read '{path}' as an image: {exc}")
    if img.format not in VALID_INPUT_FORMATS:
        raise SystemExit(
            f"error: '{path}' is {img.format}, expected one of {sorted(VALID_INPUT_FORMATS)}"
        )
    if img.width < 64 or img.height < 64:
        raise SystemExit(f"error: '{path}' is {img.width}x{img.height}, too small to be a useful source image")
    return img.convert("RGB")


def read_gltf_json(path: str):
    """Parse a GLB's JSON chunk, or return None if the file doesn't have
    one in the expected first-chunk position. Shared by validate_glb(),
    compute_bounding_box(), and check_orientation() so there's exactly one
    place that knows how to reach into a GLB's binary container -- see
    validate_glb's docstring for why this parsing exists at all (a real
    bare-geometry failure mode found by hand, once)."""
    if not os.path.isfile(path):
        raise SystemExit(f"error: input GLB not found: {path}")
    with open(path, "rb") as f:
        header = f.read(20)
        if len(header) < 20 or header[:4] != b"glTF":
            raise SystemExit(f"error: '{path}' doesn't look like a valid GLB (bad magic bytes)")
        chunk_length = int.from_bytes(header[12:16], "little")
        chunk_type = header[16:20]
        if chunk_type != b"JSON":
            return None  # unusual chunk ordering; not worth failing over
        try:
            return json.loads(f.read(chunk_length))
        except json.JSONDecodeError:
            return None


def validate_glb(path: str, log=print) -> None:
    """For --backend manual: confirm this is actually a GLB, and warn (not
    block -- an operator cataloging a deliberately-untextured mesh is a
    legitimate use) if it has no material/texture/color data at all. This
    exact failure mode (bare POSITION-only geometry, renders flat white)
    is what motivated writing this check: it was found by hand once
    already, parsing the glTF JSON chunk directly, and shouldn't need
    redoing by hand every time."""
    gltf = read_gltf_json(path)
    if gltf is None:
        return
    has_material = bool(gltf.get("materials")) or bool(gltf.get("textures"))
    has_vertex_color = any(
        "COLOR_0" in primitive.get("attributes", {})
        for mesh in gltf.get("meshes", [])
        for primitive in mesh.get("primitives", [])
    )
    if not has_material and not has_vertex_color:
        log(
            f"WARNING: {path} has no materials, textures, or vertex colors -- "
            "bare geometry only. It will render flat white. Cataloging it "
            "anyway since --backend manual doesn't second-guess what you downloaded."
        )


def compute_bounding_box(gltf: dict):
    """Union the min/max of every POSITION accessor referenced by any mesh
    primitive -- glTF 2.0 requires POSITION accessors to carry min/max
    (see the spec's accessor.min/accessor.max), so this is read directly
    off the file, never estimated or assumed. Returns None if no mesh
    declares a POSITION accessor with min/max (some malformed/unusual GLBs
    won't), so callers can distinguish "computed a real bounding box" from
    "couldn't." Units are whatever the GLB's own local coordinate space
    uses -- glTF has no mandated real-world unit, which is exactly the gap
    --scale-meters below exists to close explicitly rather than assume."""
    accessors = gltf.get("accessors", [])
    position_accessor_indices = {
        primitive["attributes"]["POSITION"]
        for mesh in gltf.get("meshes", [])
        for primitive in mesh.get("primitives", [])
        if "POSITION" in primitive.get("attributes", {})
    }
    mins, maxs = [], []
    for idx in position_accessor_indices:
        if idx >= len(accessors):
            continue
        acc = accessors[idx]
        if acc.get("min") is None or acc.get("max") is None or acc.get("type") != "VEC3":
            continue
        mins.append(acc["min"])
        maxs.append(acc["max"])
    if not mins:
        return None
    overall_min = [min(v[axis] for v in mins) for axis in range(3)]
    overall_max = [max(v[axis] for v in maxs) for axis in range(3)]
    dimensions = [overall_max[axis] - overall_min[axis] for axis in range(3)]
    return {"min": overall_min, "max": overall_max, "dimensions": dimensions}


# Below this ratio, the smallest of the three dimensions is treated as
# "effectively flat" -- a real, recurring pattern in this pipeline's own
# output (3 of the 4 GLBs already cataloged as of 2026-07-17 have exactly
# 0 depth on one axis), which nothing previously flagged. Not an error --
# a deliberately flat/billboard asset is legitimate -- but it must be
# visible, not silent, per the "may not silently redefine simulation
# dimensions" invariant this whole module exists to close.
FLAT_AXIS_RATIO = 0.02
AXIS_NAMES = ("X", "Y", "Z")


def check_orientation(bounding_box: dict) -> list[str]:
    """Soft heuristics only -- glTF's Y-up convention is a convention, not
    something this tool can verify against ground truth without a human.
    Every finding here is a warning to record and surface, never a reason
    to block cataloging."""
    warnings = []
    dims = bounding_box["dimensions"]
    largest = max(dims)
    if largest <= 0:
        warnings.append("degenerate bounding box: all three dimensions are zero or negative")
        return warnings
    for axis, size in enumerate(dims):
        if size <= 0:
            warnings.append(f"{AXIS_NAMES[axis]} axis has zero depth -- flat/billboard geometry, not full 3D")
        elif size / largest < FLAT_AXIS_RATIO:
            warnings.append(
                f"{AXIS_NAMES[axis]} axis ({size:.4f}) is under {FLAT_AXIS_RATIO*100:.0f}% of the largest "
                f"dimension ({largest:.4f}) -- effectively flat on that axis"
            )
    if dims[1] != largest and dims[1] > 0:
        warnings.append(
            f"largest dimension is on the {AXIS_NAMES[dims.index(largest)]} axis, not Y -- "
            "glTF's Y-up convention would expect height to dominate for an upright model "
            "(not necessarily wrong, e.g. for a horizontal vessel hull -- worth a human glance)"
        )
    return warnings


def strip_background(img: Image.Image, work_dir: str) -> str:
    from rembg import remove

    out = remove(img)
    path = os.path.join(work_dir, "stripped.png")
    out.save(path)
    return path


def run_backend(name: str, processed_image_path: str, work_dir: str) -> str:
    if name == "hf_spaces":
        from backends import hf_spaces
        return hf_spaces.generate(processed_image_path, work_dir)
    if name == "replicate":
        from backends import replicate as replicate_backend
        return replicate_backend.generate(processed_image_path, work_dir)
    raise SystemExit(f"error: unknown backend '{name}'")


def write_manifest_entry(
    output_name: str,
    source_image: str,
    backend: str,
    glb_path: str,
    declared_scale_meters: float | None = None,
    scale_declared_unknown: bool = False,
    log=print,
) -> None:
    os.makedirs(ASSETS_DIR, exist_ok=True)
    if os.path.isfile(MANIFEST_PATH):
        with open(MANIFEST_PATH) as f:
            manifest = json.load(f)
    else:
        manifest = {"schema_version": "monad.assetManifest.v2", "models": []}

    prior = next((m for m in manifest.get("models", []) if m["name"] == output_name), None)
    version = (prior.get("version", 0) if prior else 0) + 1

    gltf = read_gltf_json(glb_path)
    bounding_box = compute_bounding_box(gltf) if gltf is not None else None
    orientation_warnings = check_orientation(bounding_box) if bounding_box else []
    if bounding_box is None:
        log(f"WARNING: {glb_path} -- could not compute a bounding box (no POSITION accessor with min/max found).")
    for warning in orientation_warnings:
        log(f"WARNING: {output_name}: {warning}")

    if declared_scale_meters is None and not scale_declared_unknown:
        log(
            f"WARNING: {output_name} cataloged with no declared real-world scale and no explicit "
            "--scale-unknown acknowledgement. This asset's true size relative to the simulated fleet "
            "is unrecorded -- see docs/architecture/golden-hull-asset-validation-v0.1.md."
        )

    entry = {
        "name": output_name,
        "glb_path": os.path.relpath(glb_path, REPO_ROOT),
        "source_image": source_image,
        "backend": backend,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "version": version,
        "bounding_box": bounding_box,
        "orientation_warnings": orientation_warnings,
        "declared_scale_meters": declared_scale_meters,
        "scale_declared_unknown": scale_declared_unknown,
    }
    manifest["models"] = [m for m in manifest["models"] if m["name"] != output_name]
    manifest["models"].append(entry)

    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")


def run_pipeline(
    input_path: str,
    output_name: str,
    backend: str = "hf_spaces",
    source_image: str = None,
    declared_scale_meters: float | None = None,
    scale_declared_unknown: bool = False,
    log=print,
) -> dict:
    """Shared core of the CLI and serve.py's HTTP trigger -- both just
    wrap this and handle args/response differently. Runs validate ->
    strip -> infer -> write manifest -> mirror, and returns the manifest
    entry dict on success. Raises SystemExit/RuntimeError on failure,
    same as the CLI has always done -- callers decide how to present that.

    backend="manual" skips inference entirely: input_path is already a
    .glb (generated by hand through a Space's browser UI, since ZeroGPU
    Spaces reject API-originated generation calls -- see module
    docstring), so this just validates and catalogs it.
    """
    if not output_name.endswith(".glb"):
        raise SystemExit("error: output name must end in .glb")
    if declared_scale_meters is not None and scale_declared_unknown:
        raise SystemExit("error: --scale-meters and --scale-unknown are mutually exclusive")

    if backend == "manual":
        log(f"[1/2] validating {input_path} as a GLB")
        validate_glb(input_path, log=log)
        os.makedirs(ASSETS_DIR, exist_ok=True)
        final_path = os.path.join(ASSETS_DIR, output_name)
        shutil.copy(input_path, final_path)
        log(f"[2/2] writing manifest entry for {output_name}")
        write_manifest_entry(
            output_name, source_image or os.path.relpath(input_path, REPO_ROOT), backend, final_path,
            declared_scale_meters=declared_scale_meters, scale_declared_unknown=scale_declared_unknown, log=log,
        )
        log(f"done: {os.path.relpath(final_path, REPO_ROOT)}")
        with open(MANIFEST_PATH) as f:
            manifest = json.load(f)
        return next(m for m in manifest["models"] if m["name"] == output_name)

    log(f"[1/4] validating {input_path}")
    img = validate_image(input_path)

    with tempfile.TemporaryDirectory(prefix="img2asset-") as work_dir:
        log("[2/4] stripping background")
        stripped_path = strip_background(img, work_dir)

        log(f"[3/4] running inference backend: {backend}")
        raw_glb_path = run_backend(backend, stripped_path, work_dir)

        os.makedirs(ASSETS_DIR, exist_ok=True)
        final_path = os.path.join(ASSETS_DIR, output_name)
        os.replace(raw_glb_path, final_path)

    log(f"[4/4] writing manifest entry for {output_name}")
    write_manifest_entry(
        output_name, os.path.relpath(input_path, REPO_ROOT), backend, final_path,
        declared_scale_meters=declared_scale_meters, scale_declared_unknown=scale_declared_unknown, log=log,
    )

    log(f"done: {os.path.relpath(final_path, REPO_ROOT)}")
    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)
    return next(m for m in manifest["models"] if m["name"] == output_name)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="source image (PNG/JPEG/WEBP), or a .glb file with --backend manual")
    parser.add_argument("--output", required=True, help="output filename, e.g. scout-alpha.glb")
    parser.add_argument("--backend", default="hf_spaces", choices=["hf_spaces", "replicate", "manual"])
    parser.add_argument("--source", help="original source image path, recorded in the manifest (--backend manual only)")
    parser.add_argument(
        "--scale-meters", type=float, default=None,
        help="declared real-world reference dimension of this asset, in meters -- recorded explicitly in the manifest",
    )
    parser.add_argument(
        "--scale-unknown", action="store_true",
        help="explicitly acknowledge the real-world scale is not known, instead of leaving it silently unrecorded",
    )
    args = parser.parse_args()

    run_pipeline(
        args.input, args.output, args.backend, source_image=args.source,
        declared_scale_meters=args.scale_meters, scale_declared_unknown=args.scale_unknown,
    )


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    main()
