"""Web laboratory for the Monad-0 research engine.

The simulation remains backend-owned. This is the thin operator surface
served by Monad's live site; it does not duplicate engine logic.
"""
from __future__ import annotations

import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from tools.monad0.engine import CONTROLLERS, EnvironmentConfig, Sandbox

ROOT = Path(__file__).resolve().parents[1]
STATIC = Path(__file__).resolve().parent / "lab"
ARCHIVE_DIR = ROOT / "data" / "monad0-lab"


class LabSession:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.seed = 0
        self.speed = 1.0
        self.running = False
        self.tick = 0
        self.events: dict[str, list[dict]] = {}
        self.controllers = {}
        self.sandboxes = {}
        self.temporary: dict[str, list[dict]] = {}
        self.reset(0)

    def reset(self, seed: int) -> None:
        with self.lock:
            self.seed = int(seed)
            self.tick = 0
            self.running = False
            self.controllers = {klass().name: klass() for klass in CONTROLLERS}
            self.sandboxes = {name: Sandbox(EnvironmentConfig(seed=self.seed, perturbations={20: {"energy": -0.28}, 40: {"compute": -0.2}})) for name in self.controllers}
            self.events = {name: [] for name in self.controllers}
            self.temporary = {name: [] for name in self.controllers}

    def _apply_temporary(self, name: str) -> None:
        controller = self.controllers[name]
        for item in self.temporary[name]:
            if item["until"] <= self.tick:
                continue
            if item["type"] == "POLICY_BIAS_INJECTION":
                controller.parameters.exploration_rate = min(1.0, controller.parameters.exploration_rate + 0.35)
            elif item["type"] == "MEMORY_ACCESS_REDUCTION":
                controller.parameters.model_query_frequency = min(32, controller.parameters.model_query_frequency + 2)
            elif item["type"] == "MODEL_TARGET_DRIFT":
                controller.predicted_viability = min(1.0, controller.predicted_viability + 0.15)

    def step(self) -> None:
        with self.lock:
            for name, controller in self.controllers.items():
                self._apply_temporary(name)
                events = controller.tick(self.sandboxes[name])
                self.events[name].extend(events)
            self.tick += 1
            for name in self.temporary:
                self.temporary[name] = [item for item in self.temporary[name] if item["until"] > self.tick]

    def snapshot(self) -> dict:
        with self.lock:
            systems = {}
            for name, controller in self.controllers.items():
                model = controller.self_model
                pending = controller.pending.as_dict() if controller.pending else None
                systems[name] = {
                    "state": self.sandboxes[name].state.as_dict(),
                    "action": self.sandboxes[name].last_action,
                    "parameters": controller.parameters.as_dict(),
                    "pending_contract": pending,
                    "contracts_confirmed": controller.contracts_confirmed,
                    "contracts_refuted": controller.contracts_refuted,
                    "hypotheses": list(model.hypotheses.values()) if model else [],
                    "graph": model.snapshot() if model else {"nodes": {}, "edges": {}},
                    "recent_events": self.events[name][-12:],
                }
            return {"seed": self.seed, "tick": self.tick, "running": self.running, "speed": self.speed, "systems": systems}

    def perturb(self, name: str, probe_type: str, duration: int) -> None:
        if name not in self.controllers:
            raise ValueError("unknown system")
        if probe_type not in {"MEMORY_ACCESS_REDUCTION", "POLICY_BIAS_INJECTION", "MODEL_TARGET_DRIFT", "NO_OP"}:
            raise ValueError("unknown perturbation")
        self.temporary[name].append({"type": probe_type, "until": self.tick + max(1, int(duration))})

    def contract_action(self, name: str, action: str, value: float | None = None) -> None:
        controller = self.controllers.get(name)
        if not controller or not controller.pending:
            raise ValueError("no pending contract")
        contract = controller.pending
        if action == "reject":
            setattr(controller.parameters, contract.target_parameter, contract.baseline_value)
            contract.status = "rejected-by-operator"
            controller.pending = None
        elif action == "modify":
            if value is None:
                raise ValueError("modified value required")
            contract.proposed_value = float(value)
            setattr(controller.parameters, contract.target_parameter, float(value))
            contract.status = "modified-by-operator"
        elif action == "approve":
            contract.status = "approved-by-operator"
        else:
            raise ValueError("unknown contract action")

    def archive(self) -> str:
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        name = f"seed-{self.seed}-tick-{self.tick}-{int(time.time())}.json"
        payload = {"seed": self.seed, "tick": self.tick, "systems": self.events}
        (ARCHIVE_DIR / name).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        return name

    def replay(self, name: str) -> dict:
        path = (ARCHIVE_DIR / name).resolve()
        if path.parent != ARCHIVE_DIR.resolve() or not path.is_file():
            raise ValueError("archive not found")
        payload = json.loads(path.read_text())
        return {"replay": True, **payload}


SESSION = LabSession()


class Handler(BaseHTTPRequestHandler):
    def _json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, sort_keys=True).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/state":
            self._json(SESSION.snapshot())
        elif parsed.path == "/api/archives":
            ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
            self._json({"archives": sorted(path.name for path in ARCHIVE_DIR.glob("*.json"))})
        elif parsed.path == "/api/replay":
            try:
                self._json(SESSION.replay(parse_qs(parsed.query).get("name", [""])[0]))
            except ValueError as exc:
                self._json({"error": str(exc)}, 404)
        elif parsed.path in {"/", "/index.html"}:
            body = (STATIC / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self) -> None:  # noqa: N802
        try:
            body = self._body()
            if self.path == "/api/reset":
                SESSION.reset(body.get("seed", 0))
            elif self.path == "/api/step":
                SESSION.step()
            elif self.path == "/api/control":
                action = body.get("action")
                if action == "start": SESSION.running = True
                elif action == "pause": SESSION.running = False
                elif action == "step": SESSION.step()
                elif action == "reset": SESSION.reset(body.get("seed", SESSION.seed))
                elif action == "speed": SESSION.speed = max(0.1, min(20.0, float(body.get("value", 1))))
            elif self.path == "/api/perturb":
                SESSION.perturb(body["system"], body["type"], body.get("duration", 10))
            elif self.path == "/api/contract":
                SESSION.contract_action(body["system"], body["action"], body.get("value"))
            elif self.path == "/api/archive":
                self._json({"archive": SESSION.archive()})
                return
            else:
                self._json({"error": "not found"}, 404)
                return
            self._json(SESSION.snapshot())
        except (KeyError, TypeError, ValueError) as exc:
            self._json({"error": str(exc)}, 400)

    def log_message(self, *_args) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve the Monad-0 web laboratory")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Monad-0 Web Laboratory: http://{args.host}:{args.port}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
