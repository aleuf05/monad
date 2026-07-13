"""Free-tier backend: stabilityai/stable-fast-3d's public Gradio Space.

UV-textured GLB by design. Replaces an earlier stabilityai/TripoSR
integration: as of 2026-07-12, TripoSR's /generate endpoint AppError'd
for every call tested -- anonymous AND authenticated with a verified-valid
HF_TOKEN (confirmed via GET /api/whoami-v2 returning 200), so this wasn't
the usual "anonymous ZeroGPU quota" story the old code assumed. A separate
attempt against frogleo/Image-to-3D did return a .glb with no AppError,
but the file itself had zero materials/textures/color data (bare POSITION
geometry only, confirmed by parsing the glTF JSON chunk directly) -- not
usable either.

Gated: requires accepting this Space's terms once at
https://huggingface.co/spaces/stabilityai/stable-fast-3d before HF_TOKEN
can call it. If this raises a permission-shaped error, that's the first
thing to check, not a code bug -- verified working here with a token that
already had access; behavior for a token that hasn't accepted the terms
yet is untested.

Fallback if this Space goes down too: tencent/Hunyuan3D-2 (not 2.1 --
skip that one) via its generation_all endpoint. Verify the exact api_name
with Client(space_id).view_api() before wiring it in, the same way this
file's own /run_button endpoint was discovered, rather than guessing.
"""
import os
import shutil
import time

from gradio_client import Client, handle_file

SPACE_ID = "stabilityai/stable-fast-3d"
FOREGROUND_RATIO = 0.85
REMESH_OPTION = "None"  # Literal['None', 'Triangle', 'Quad']
VERTEX_COUNT = -1  # -1 = auto
TEXTURE_SIZE = 1024
MAX_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 5


def generate(processed_image_path: str, out_dir: str) -> str:
    token = os.environ.get("HF_TOKEN")
    client = Client(SPACE_ID, token=token)

    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            _preview, model_path = client.predict(
                handle_file(processed_image_path),
                FOREGROUND_RATIO,
                REMESH_OPTION,
                VERTEX_COUNT,
                TEXTURE_SIZE,
                api_name="/run_button",
            )
            ext = os.path.splitext(model_path)[1] or ".glb"
            dest = os.path.join(out_dir, f"_hf_spaces_raw{ext}")
            shutil.copy(model_path, dest)
            return dest
        except Exception as exc:  # gradio_client.exceptions.AppError, network errors, etc.
            last_error = exc
            if attempt < MAX_ATTEMPTS:
                time.sleep(RETRY_DELAY_SECONDS)

    raise RuntimeError(
        f"hf_spaces backend failed after {MAX_ATTEMPTS} attempts against "
        f"{SPACE_ID}. Last error: {last_error}. If this looks permission-"
        "shaped, confirm the HF_TOKEN's account has accepted this Space's "
        "gated terms at https://huggingface.co/spaces/stabilityai/stable-fast-3d "
        "-- otherwise retry, or fall back to tencent/Hunyuan3D-2 (not 2.1)."
    ) from last_error
