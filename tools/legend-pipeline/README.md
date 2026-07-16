# Legend Pipeline

Monad's Gemini legend path assembles authoritative
mission evidence, renders a sober factual account, prepares a model-neutral
generation request, and validates returned legend candidates. It does not
approve or publish lore.

Prepare a request from a real mission:

```sh
python3 tools/legend-pipeline/legend_pipeline.py prepare \
  web/archive/missions/quacken-transit-002/mission.json
```

For offline validation, a candidate must contain `title`, `mythology`, `classification`
(`fleet-lore`), and `source_ids`. Save that JSON, then validate it:

```sh
python3 tools/legend-pipeline/legend_pipeline.py validate \
  web/archive/missions/quacken-transit-002/mission.json candidate.json
```

Generate live through the commissioned Gemini provider and atomically write a
Mission Record-compatible, review-required artifact:

```sh
GEMINI_API_KEY=... python3 tools/legend-pipeline/legend_pipeline.py generate \
  web/archive/missions/quacken-transit-002/mission.json \
  --artifact-output data/legend-artifacts/quacken-transit-002.json
```

The output remains `review-required`; generation and validation never approve
or publish fleet lore. The API key is read only from the environment.
