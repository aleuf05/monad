"""Free-tier backend: stabilityai/TripoSR's public Gradio Space.

No API key required for anonymous use, but anonymous calls share a
ZeroGPU queue with everyone else hitting the same public demo -- expect
occasional AppError failures under load with no useful detail (the Space
doesn't run with verbose error reporting). Set HF_TOKEN (a free
huggingface.co account token) to get authenticated queue priority, which
noticeably reduces how often this happens.

Verified 2026-07-12: /preprocess succeeded on every call tested;
/generate returned a generic AppError on every anonymous call tested
(both a flat-shaded and a gradient-shaded synthetic image). Consistent
with anonymous ZeroGPU quota exhaustion, not an integration bug --
retry, supply HF_TOKEN, or fall back to the replicate backend if this
keeps happening.
"""
import os
import shutil
import time

from gradio_client import Client, handle_file

SPACE_ID = "stabilityai/TripoSR"
PREPROCESS_FOREGROUND_RATIO = 0.85
GENERATE_RESOLUTION = 256
MAX_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 5


def generate(processed_image_path: str, out_dir: str) -> str:
    token = os.environ.get("HF_TOKEN")
    client = Client(SPACE_ID, token=token)

    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            processed = client.predict(
                handle_file(processed_image_path),
                False,  # remove_background: our own rembg step already did this
                PREPROCESS_FOREGROUND_RATIO,
                api_name="/preprocess",
            )
            _obj_path, glb_path = client.predict(
                processed,
                GENERATE_RESOLUTION,
                api_name="/generate",
            )
            dest = os.path.join(out_dir, "_hf_spaces_raw.glb")
            shutil.copy(glb_path, dest)
            return dest
        except Exception as exc:  # gradio_client.exceptions.AppError, network errors, etc.
            last_error = exc
            if attempt < MAX_ATTEMPTS:
                time.sleep(RETRY_DELAY_SECONDS)

    raise RuntimeError(
        f"hf_spaces backend failed after {MAX_ATTEMPTS} attempts against "
        f"{SPACE_ID}. Last error: {last_error}. This public Space "
        "occasionally rejects anonymous calls under ZeroGPU load -- set "
        "HF_TOKEN for priority queueing, or retry, or use --backend "
        "replicate."
    ) from last_error
