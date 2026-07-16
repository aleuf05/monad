# Monad Rich Voice Engine

This is the backend-only, cache-first Gemini TTS tier behind Character Voice Studio. Browser Speech remains the free rehearsal tier.

## Cost boundary

- `GET /status`, `GET /budget`, and `POST /estimate` never call Gemini.
- `POST /render` checks the immutable artifact cache before reserving budget.
- Default daily limits are `$0.10` and `300` generated seconds.
- A failed provider request is recorded as failed and releases its reservation.
- The Studio never renders on slider or text changes. The operator must estimate, then explicitly generate.

## Configuration

The systemd unit optionally reads `/home/cgl/.config/monad/gemini.env`:

```text
GEMINI_API_KEY=your-key
```

The file is operator-owned, must not enter Git, and needs no `sudo` to create. Without it, status and estimates work while new rich renders return a clear unconfigured response. Cached artifacts remain readable.

Optional service overrides:

```text
MONAD_VOICE_DAILY_USD=0.10
MONAD_VOICE_DAILY_SECONDS=300
```

The committed unit fixes those conservative defaults. Raise them only through an intentional service change.

## Tests

```bash
python3 -m unittest discover -s tools/voice-engine -p 'test_*.py'
python3 -m py_compile tools/voice-engine/*.py
```

Tests use fake PCM providers and make no external calls.

## Local unconfigured smoke test

```bash
python3 tools/voice-engine/server.py
curl http://127.0.0.1:4775/status
curl -X POST -H 'Content-Type: application/json' \
  -d '{"character_id":"captain.monad","transcript":"Hold station."}' \
  http://127.0.0.1:4775/estimate
```

Stop the server immediately after the check. The commissioned service is loopback-only and publicly reached through `/voice-api/*`.

## First commissioned proof

1. Confirm `/voice-api/status` says `configured: true` and shows zero or expected spend.
2. In Character Voice Studio, rehearse free.
3. Estimate one short Captain line.
4. Generate exactly one rich take.
5. Record the artifact hash, duration, cost, voice and listener impression.
6. Estimate and render the identical request again; it must report a cache hit and unchanged spend.
7. Do not connect Radio until blind listening evaluation passes.

## Listening evaluation

`evaluation.py` creates a private answer manifest and a public blinded manifest from existing artifact URLs. It never generates audio. The pass gate is character recognition `>=75%`, intent recognition `>=80%`, caricature `<10%`, and zero transcript errors.
