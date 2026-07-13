# img2asset

Image -> 3D asset pipeline. Takes a source image, strips the background,
runs image-to-3D inference on a remote GPU (no local GPU available on
Granite/Rock64), and drops a `.glb` into `web/assets/models/` with a
manifest entry. Live-served directly, no deploy step (see
docs/deployment.md) -- a successful run is viewable immediately at
`toys/asset-viewer/`. Contracts-only: never touches FleetCore or `World`
state.

## Setup

```sh
cd tools/img2asset
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```sh
python3 image_to_asset.py input/<source>.png --output <name>.glb
```

Source images go in `input/` (gitignored). Output lands in
`web/assets/models/<name>.glb`; `manifest.json` next to it gets an entry
recording the name, source image, backend used, and timestamp. View
results at `toys/asset-viewer/` (or its `web/` copy) -- it reads the
manifest and lists every cataloged model.

## Backends

- `--backend hf_spaces` (default) -- free, no API key required. Calls
  `stabilityai/TripoSR`'s public Gradio Space. Set `HF_TOKEN` (a free
  huggingface.co account token) to get authenticated queue priority.
  **Known issue, verified 2026-07-12:** anonymous calls to this shared
  Space's `/generate` endpoint failed consistently in testing (likely
  ZeroGPU quota exhaustion under load, not an integration bug --
  `/preprocess` succeeded every time). If this keeps happening, set
  `HF_TOKEN` first before assuming the pipeline itself is broken.
- `--backend replicate` -- paid, real cost (per-second GPU billing).
  Dormant until `REPLICATE_API_TOKEN` is set — **do not set that token
  without Captain T's approval**, per the tasking packet's own gate.
  **Unverified**: written against Replicate's documented API shape but
  never actually called (no token available to test with in this
  environment). Confirm the current best image-to-3D model on
  https://replicate.com/explore and update `REPLICATE_MODEL` in
  `backends/replicate.py` before the first real run.

## Manifest convention

`web/assets/models/manifest.json` is new -- there was no existing 3D
asset manifest in this repo before this tool (checked before building:
no `.glb` files, no 3D asset directory anywhere). Shape:

```json
{
  "schema_version": "monad.assetManifest.v1",
  "models": [
    {
      "name": "scout-alpha.glb",
      "glb_path": "web/assets/models/scout-alpha.glb",
      "source_image": "tools/img2asset/input/scout-alpha-src.png",
      "backend": "hf_spaces",
      "created_at": "2026-07-12T16:40:00+00:00"
    }
  ]
}
```

`toys/asset-viewer/` (see its own README) consumes this manifest to
list and render every cataloged model with `<model-viewer>`.
