# Legend Pipeline

Component one of Monad's legend-generation path. It assembles authoritative
mission evidence, renders a sober factual account, prepares a model-neutral
generation request, and validates returned legend candidates. It does not
approve or publish lore.

Prepare a request from a real mission:

```sh
python3 tools/legend-pipeline/legend_pipeline.py prepare \
  web/missions/quacken-transit-002/mission.json
```

A model/provider must return JSON with `title`, `mythology`, `classification`
(`fleet-lore`), and `source_ids`. Save that JSON, then validate it:

```sh
python3 tools/legend-pipeline/legend_pipeline.py validate \
  web/missions/quacken-transit-002/mission.json candidate.json
```

No provider is selected here on purpose. `prepare` is the stable adapter
boundary; credentials and provider choice belong to the caller. The tool never
passes template prose off as generated output.
