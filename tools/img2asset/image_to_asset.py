#!/usr/bin/env python3
"""Image -> 3D asset pipeline for Monad. Contracts-only: this tool never
touches FleetCore or World state, it only reads a source image and
writes a .glb file plus a manifest entry under web/assets/models/ (and
mirrors both into web-lan/assets/models/, same manual-sync pattern
toys/<name>/ already uses -- both dirs are live-served directly, no
deploy step, see docs/deployment.md).

Usage:
    image_to_asset.py <input.png> --output <name>.glb [--backend hf_spaces|replicate]
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
LAN_ASSETS_DIR = os.path.join(REPO_ROOT, "web-lan", "assets", "models")
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


def write_manifest_entry(output_name: str, source_image: str, backend: str, glb_path: str) -> None:
    os.makedirs(ASSETS_DIR, exist_ok=True)
    if os.path.isfile(MANIFEST_PATH):
        with open(MANIFEST_PATH) as f:
            manifest = json.load(f)
    else:
        manifest = {"schema_version": "monad.assetManifest.v1", "models": []}

    entry = {
        "name": output_name,
        "glb_path": os.path.relpath(glb_path, REPO_ROOT),
        "source_image": source_image,
        "backend": backend,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    manifest["models"] = [m for m in manifest["models"] if m["name"] != output_name]
    manifest["models"].append(entry)

    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")


def mirror_to_lan(glb_filename: str) -> None:
    os.makedirs(LAN_ASSETS_DIR, exist_ok=True)
    shutil.copy(os.path.join(ASSETS_DIR, glb_filename), os.path.join(LAN_ASSETS_DIR, glb_filename))
    shutil.copy(MANIFEST_PATH, os.path.join(LAN_ASSETS_DIR, "manifest.json"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="source image (PNG/JPEG/WEBP)")
    parser.add_argument("--output", required=True, help="output filename, e.g. scout-alpha.glb")
    parser.add_argument("--backend", default="hf_spaces", choices=["hf_spaces", "replicate"])
    args = parser.parse_args()

    if not args.output.endswith(".glb"):
        raise SystemExit("error: --output must end in .glb")

    print(f"[1/4] validating {args.input}")
    img = validate_image(args.input)

    with tempfile.TemporaryDirectory(prefix="img2asset-") as work_dir:
        print("[2/4] stripping background")
        stripped_path = strip_background(img, work_dir)

        print(f"[3/4] running inference backend: {args.backend}")
        raw_glb_path = run_backend(args.backend, stripped_path, work_dir)

        os.makedirs(ASSETS_DIR, exist_ok=True)
        final_path = os.path.join(ASSETS_DIR, args.output)
        os.replace(raw_glb_path, final_path)

    print(f"[4/4] writing manifest entry for {args.output}")
    write_manifest_entry(args.output, os.path.relpath(args.input, REPO_ROOT), args.backend, final_path)
    mirror_to_lan(args.output)

    print(f"done: {os.path.relpath(final_path, REPO_ROOT)} (mirrored to web-lan/)")


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    main()
