"""Paid backend: Replicate's hosted TripoSR/SF3D API.

Dormant by design -- does nothing without REPLICATE_API_TOKEN set, per
the tasking packet's own gate ("flag for Captain T approval if cost
involved"). Replicate bills per second of GPU time; do not set the
token until that approval is in.

UNVERIFIED: written against Replicate's documented API shape but never
actually called (no token available in this environment to test with).
REPLICATE_MODEL's default is a plausible public TripoSR model slug, not
a confirmed-working one -- check https://replicate.com/explore for the
current best image-to-3D model and its exact owner/name:version string
before the first real run, and update the default below once confirmed.
"""
import os
import shutil

REPLICATE_MODEL = os.environ.get("REPLICATE_MODEL", "camenduru/tripo-sr")


def generate(processed_image_path: str, out_dir: str) -> str:
    token = os.environ.get("REPLICATE_API_TOKEN")
    if not token:
        raise RuntimeError(
            "replicate backend requires REPLICATE_API_TOKEN (real cost, "
            "needs Captain T approval per the tasking packet -- see "
            "tools/img2asset/README.md). Not set; refusing to call out."
        )

    import replicate as replicate_sdk  # imported lazily so it's an optional dep until used

    with open(processed_image_path, "rb") as image_file:
        output = replicate_sdk.run(REPLICATE_MODEL, input={"image": image_file})

    # replicate.run's return shape varies by model (single FileOutput vs.
    # dict of named outputs) -- handle both rather than assume.
    glb_url = output if isinstance(output, str) else output.get("mesh") or output.get("glb")
    if not glb_url:
        raise RuntimeError(f"replicate backend: could not find a GLB output in response: {output!r}")

    import urllib.request

    dest = os.path.join(out_dir, "_replicate_raw.glb")
    urllib.request.urlretrieve(str(glb_url), dest)
    return dest
