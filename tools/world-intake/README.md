# Living World Intake V0.1

A deliberately narrow SQLite-backed intake spine. It preserves pasted source
bytes, deterministically extracts candidate assertions, resolves identities,
surfaces conflicts, records Captain adjudication, and compiles approved
proposals. It never writes canonical state: callers must submit the compiled
`apply-canon-change` JSON through FleetCore's authenticated `/command` path.

## Run

```sh
python3 tools/world-intake/world_intake.py --db data/world-intake.sqlite3 ingest \
  tools/world-intake/first_wave_reactor_crew.txt --author Monad --mission-context first-wave
python3 tools/world-intake/world_intake.py --db data/world-intake.sqlite3 extract SOURCE_ID
python3 tools/world-intake/world_intake.py --db data/world-intake.sqlite3 queue --source-id SOURCE_ID
python3 tools/world-intake/world_intake.py --db data/world-intake.sqlite3 review ASSERTION_ID approve
python3 -m unittest tools/world-intake/test_world_intake.py
```

The review API is a loopback service with authenticated adjudication writes:

```sh
WORLD_INTAKE_REVIEW_TOKEN='operator-secret' \
  python3 tools/world-intake/world_intake.py --db data/world-intake.sqlite3 serve
```

Production installation uses `scripts/install-world-intake.sh`, its systemd
unit, and Caddy's `/world-intake-api/*` route. The installer creates the review
token at `~/.config/monad/world-intake.env` with owner-only permissions when it
does not already exist.

`Intake.compile(adjudication_id)` returns `(command_id, payload)`. The embedding
service supplies `Intake.commit(command_id, submit)`, where `submit(payload,
idempotency_key)` performs authentication and calls FleetCore. A rejected result
remains in `commands`; an accepted result creates a linked local receipt in
`canon_events`. FleetCore remains the only canon owner.

## Storage and safety

The schema has immutable-content `sources`, proposed `assertions`, optional
`entities`/`resolutions`, material `conflicts`, append-only `adjudications`,
idempotent `commands`, FleetCore `canon_events`, and compensating `corrections`.
The source content hash deduplicates retries; stable assertion, adjudication,
command, and event IDs make replay safe across restarts. Corrections never edit
or delete prior history.

Known limitations: extraction is intentionally fixture-shaped and deterministic,
not a general natural-language endpoint. Station knowledge is limited to the
Deck 7 intake scope. Role exclusivity is a small V0.1 policy set. The generic
tool deliberately has no unrestricted prose-to-command endpoint and no automatic
approval. The embedding service must supply the authenticated FleetCore submit
callback; rejected responses remain inspectable in the local command record.
