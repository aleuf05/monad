# Monad libfive headless pipeline

```sh
python3 tools/libfive/generate.py status
python3 tools/libfive/generate.py generate sphere demo-sphere --radius 12
```

The wrapper accepts named primitives only (`sphere`, `box`, `torus`), writes a
temporary Studio/Guile source, invokes the pinned official `export-meshes`, and
records STL provenance in `web/assets/libfive/manifest.json`. It never exposes
arbitrary Scheme over HTTP.
