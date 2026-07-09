# Monad Watchman

Watchman is a permanent, non-LLM heartbeat process. Every five minutes it
appends one JSON object to:

```text
logs/agents/watchman/YYYY/YYYY-MM-DD_watch.jsonl
```

Each entry records UTC time, hostname, system uptime when available, the
current Git commit, repository path, disk capacity, and local Qdrant health.
Watchman reads repository state but writes only to its own log directory.

## Granite Installation

The service file assumes the Granite account is `cgl` and the repository is
located at `/home/cgl/dev/monad`. Adjust `User`, `WorkingDirectory`, and
`ExecStart` before installation if Granite differs.

```sh
cd ~/dev/monad
sudo cp systemd/monad-watchman.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable monad-watchman
sudo systemctl start monad-watchman
sudo systemctl status monad-watchman
```

The Qdrant health endpoint defaults to `http://127.0.0.1:6333/healthz`. Set
`MONAD_QDRANT_HEALTH_URL` in the service if the local endpoint differs.

## Local Test

Write one heartbeat and exit:

```sh
./watchman.py --once
```

The test appends a real entry to Watchman's own daily log. It does not modify
Helmsman or Captain logs.
