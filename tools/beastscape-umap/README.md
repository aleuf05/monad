# Beastscape local UMAP stack

Project-local Python environment for learning a three-coordinate navigational
chart over a pre-existing, high-dimensional specimen atlas.

The stack is deliberately separate from the live editor at this checkpoint:
this proves the mapper can fit structural descriptors and transform new
descriptors before it is wired into Beastscape.

## Rebuild

```bash
python3 -m venv tools/beastscape-umap/.venv
tools/beastscape-umap/.venv/bin/python -m pip install \
  -r tools/beastscape-umap/requirements.txt
```

## Verify

```bash
tools/beastscape-umap/.venv/bin/python \
  tools/beastscape-umap/verify_stack.py
```

Success emits JSON with `"status": "ready"`, a `360 × 3` learned chart,
an out-of-sample transform, finite coordinates, and neighborhood
trustworthiness of at least `0.90`.

No system packages, service, daemon, or sudo handoff are required.

## Build and verify the first atlas

```bash
tools/beastscape-umap/.venv/bin/python \
  tools/beastscape-umap/build_atlas.py
tools/beastscape-umap/.venv/bin/python \
  tools/beastscape-umap/verify_atlas.py
```

The build deterministically exports the first Beastscape Foundry comparison to
`web/toys/beastscape/umap-atlas.v1.json`: three candidate developmental
grammars, 720 atlas soundings per candidate, structural evidence, and an
independently learned three-dimensional UMAP Passage for each. The browser
continuously decodes between local soundings; they define each candidate's
geography without limiting navigation to stored specimens.
