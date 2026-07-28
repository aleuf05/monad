# Kraken First Contact

Date: 2026-07-28

Status: verified live render

## Durable evidence

- Live URL: `https://cameronlampley.com/toys/periscope/`
- Active browser asset URL: `/assets/intake/kraken_tripo_v1.glb`
- Preserved original: `assets/intake/originals/21ddb560-0090-40e0-a0df-948e99dcd171_5fc12f696f79cffe6e53a5ddbc992b3f.glb`
- Working copy: `assets/intake/kraken_tripo_v1.glb`
- SHA-256: `3cbded33cc1c21eaac896bbebe2987bede1e9a0248e08984d6be2ea1000cab3e`
- Size: 62,131,344 bytes
- Screenshot: `docs/reports/assets/2026-07-28-kraken-first-contact.png`

The original and working-copy hashes matched at first contact. The original
export was not optimized, decimated, recompressed, or otherwise transformed.

## Inspection

- Valid GLB 2 container
- Meshes: 1
- Triangles: 1,953,876
- Materials: 1
- Embedded textures: 3 JPEG images (base color, normal, roughness/metallic)
- Animations: 0
- Skins: 0

## Live verification

Headless Chromium loaded the real public Periscope page and received HTTP 200
for the 62,131,344-byte Kraken GLB. The page created a WebGL2 context, showed
`KRAKEN — NEW` in field at bearing 000°, and rendered a recognizable textured
blue octopus in the glass. No page error, request failure, or console error
occurred. Headless Chromium emitted only GPU-stall warnings caused by the
verification script's explicit `readPixels` call.

The first-contact implementation labels the creature as a simulated 3D
contact. It is presentation-local and is not yet a FleetCore world fact.
