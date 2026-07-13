"""Paid backend: Replicate's tencent/hunyuan-3d-3.1.

Verified working 2026-07-12: a real end-to-end run against the ducky
source image produced a properly UV-textured .glb (materials, textures,
TEXCOORD_0 all present, confirmed by parsing the glTF JSON chunk
directly) -- unlike every ZeroGPU Space tried (see hf_spaces.py's
docstring for that whole investigation). Replicate is a real API
product, not a community demo -- no ZeroGPU-style gate, plain
server-to-server calls work fine, which is the entire reason this
backend exists alongside the manual one.

Dormant without REPLICATE_API_TOKEN set, per the tasking packet's own
gate ("flag for Captain T approval if cost involved"). Replicate bills
per second of GPU time against whatever account the token belongs to.

generate_type is explicitly forced to "Normal" -- the model's own schema
documents "Geometry" as the bare-untextured-mesh option, which is
exactly the failure mode this whole backend swap was trying to avoid.
"""
import base64
import mimetypes
import os

REPLICATE_MODEL = os.environ.get("REPLICATE_MODEL", "tencent/hunyuan-3d-3.1")


def generate(processed_image_path: str, out_dir: str) -> str:
    token = os.environ.get("REPLICATE_API_TOKEN")
    if not token:
        raise RuntimeError(
            "replicate backend requires REPLICATE_API_TOKEN (real cost, "
            "needs approval per the tasking packet -- see "
            "tools/img2asset/README.md). Not set; refusing to call out."
        )

    import replicate as replicate_sdk  # imported lazily so it's an optional dep until used

    client = replicate_sdk.Client(api_token=token)

    # Two prior attempts both failed with "Unsupported image format: .":
    # first via run()'s automatic file handling (a raw open file handle,
    # uploaded through client.files.create() with no filename set), then
    # via an explicit files.create(..., filename=...) call. Both produce
    # an api.replicate.com/v1/files/... URL -- comparing against the one
    # real successful prediction (done through Replicate's own website,
    # which uses a replicate.delivery/... CDN URL instead) confirmed the
    # model container can't fetch the files-API URL at all, regardless of
    # its filename/extension. Embedding the image directly as a base64
    # data URI sidesteps the whole fetch-a-URL step -- the model receives
    # the bytes inline, no second network hop for it to fail on.
    mime_type = mimetypes.guess_type(processed_image_path)[0] or "image/png"
    with open(processed_image_path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode("utf-8")
    data_uri = f"data:{mime_type};base64,{encoded}"

    output = client.run(
        REPLICATE_MODEL,
        input={
            "image": data_uri,
            "generate_type": "Normal",
            "enable_pbr": True,
        },
    )

    # replicate>=1.0's run() wraps single-file outputs in a FileOutput
    # (has .read(), not a plain str) rather than always returning a raw
    # URL string -- the old version of this file assumed isinstance(output,
    # str) and would have broken on that. Handle both.
    dest = os.path.join(out_dir, "_replicate_raw.glb")
    if hasattr(output, "read"):
        with open(dest, "wb") as f:
            f.write(output.read())
    else:
        import urllib.request
        urllib.request.urlretrieve(str(output), dest)
    return dest
