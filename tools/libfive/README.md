# Monad libfive headless pipeline

```sh
python3 tools/libfive/generate.py status
python3 tools/libfive/generate.py generate sphere demo-sphere --radius 12
```

The wrapper accepts named primitives only (`sphere`, `box`, `torus`), writes a
temporary Studio/Guile source, invokes the pinned official `export-meshes`, and
records STL provenance in `web/assets/libfive/manifest.json`.

The Shape Foundry also accepts native libfive/Guile text sources (`.io`, `.scm`,
and `.ss`, up to 64 KB) through the sandboxed API and records both source and
output hashes. STEP, OpenSCAD, Python, and other formats need separate
toolchains and are intentionally not guessed at.
