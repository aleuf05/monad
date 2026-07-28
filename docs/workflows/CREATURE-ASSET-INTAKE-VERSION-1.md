# Creature Asset Intake — Version 1

Use this gate for every creature GLB.

## Gate

1. Preserve the original export under `assets/intake/originals/`.
2. Record its byte size and SHA-256.
3. Validate the GLB header and inspect meshes, triangles, materials, embedded
   textures, animations, skins, bounds, orientation, and rendering.
4. Create a separately named working copy under `assets/intake/`.
5. Confirm the original and initial working-copy hashes match.
6. Add a disabled creature-manifest entry with:
   `id`, `display_name`, `model_path`, `enabled`, `position`, `rotation`,
   `scale`, and `contact_label`.
7. Stage the render by enabling the manifest entry. Do not add a bespoke
   loader.
8. Verify the real Periscope URL, GLB network response, browser console,
   framing, lighting, selection, and reload behavior.
9. Archive one screenshot and a concise evidence report.
10. Obtain operator acceptance before treating the render as promoted.

## Boundaries

- Never optimize, decimate, recompress, overwrite, or delete the preserved
  original during intake.
- Never infer real-world scale from generated geometry. Record unknown scale
  honestly until a human or authoritative source declares it.
- The creature manifest owns rendering configuration, not world truth.
- FleetCore owns production creature existence, position, motion, and state.
- Presentation-staged positions must be visibly labeled as staged until
  FleetCore provides them.

## Rollback

Set the manifest entry's `enabled` field to `false`. This removes the staged
render without changing the GLB, other manifest entries, or FleetCore.
