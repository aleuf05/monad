# Durability: systemd Units for FleetCore and the LAN Web Server

Date: 2026-07-13
Operator: Lt. cgl
Objective: make `fleetcore-serve` and the LAN web server survive a Granite reboot — both were still ad hoc `nohup` processes, confirmed by checking `systemctl is-enabled`/`is-active` and the absence of `/etc/systemd/system/fleetcore-serve.service`.

## What a reboot would have done, before this watch

- Caddy: fine — `enabled` and `active`, survives reboot on its own. The static site (once `web/` is deployed) comes back automatically.
- `fleetcore-serve`: gone. Not installed as a systemd unit. Every live-mode feature across every toy (Fleet Motion, Periscope, Bridge, FleetCore Control Center, Harbor Pilot Boarding, despawn, land enforcement) would silently fall back to disconnected/read-only until manually restarted.
- `web-lan/`'s LAN server (`python3 -m http.server 8090`): also gone, no unit at all. Every LAN toy unreachable until manually restarted.

## Fix

- `scripts/fleetcore-serve.service`: updated `ExecStart` to `--port 4771 --bind-all --command-token bridge-3-0-lan` — this box's actual live configuration, not the more conservative loopback-only/read-only default it originally shipped with. Installing the old version as-is would have been a real capability regression on every reboot (Bridge/FleetCore Control Center/LAN toys silently losing write access and LAN reachability), not just a durability fix. Comments rewritten to explain why, and to point at `docs/deployment.md`'s token-exposure history rather than re-describe it.
- `scripts/monad-lan-web.service` (new): serves `web-lan/` on port `8090`, `--bind 0.0.0.0`, matching the LAN server's current invocation exactly.
- `docs/deployment.md`: updated "Running the process" with the current install commands (now installing both units together) and current `ExecStart` contents; simplified the "Durability" note to point back at that section instead of duplicating the commands.

## Verification

- `systemd-analyze verify` on both unit files: clean, no errors.
- Confirmed every path each `ExecStart` references actually exists: the `serve` binary, `python3`, and `web-lan/`.
- Did not install either unit — that needs `sudo`, which this session can't supply. Left for the operator to run:

```sh
sudo cp scripts/fleetcore-serve.service scripts/monad-lan-web.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now fleetcore-serve monad-lan-web
sudo systemctl status fleetcore-serve monad-lan-web
```

Note for whoever runs this: `enable --now` will restart `fleetcore-serve` under systemd management, replacing the currently-running ad hoc process. State is preserved either way (`data/fleetcore/` on disk), same as every manual restart this session, but worth knowing it's not a no-op if something is expected to keep running completely undisturbed at that exact moment.

## Not done

- Did not rotate `bridge-3-0-lan` — explicitly out of scope per prior direction this session ("don't rotate"). Documented plainly in both the unit file and `docs/deployment.md` instead.
- Did not install the units — needs `sudo`, left for the operator.

## Updated

- `scripts/fleetcore-serve.service`
- `scripts/monad-lan-web.service` (new)
- `docs/deployment.md`
