"""Image-to-3D inference backends. Each backend exports one function:

    generate(processed_image_path: str, out_dir: str) -> str

which takes a background-stripped, format-validated PNG and returns the
path to a downloaded .glb file. Backend selection happens in
image_to_asset.py, not here -- these modules have no knowledge of each
other or of the CLI.
"""
