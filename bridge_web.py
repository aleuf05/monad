import argparse
import json
import sys
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import bridge

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_REFRESH = 5.0
DEFAULT_ENGINE_INTERVAL = 60.0
DEFAULT_TIMEOUT = 3.0


HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Monad Bridge</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0c0f12;
      --panel: #151a1f;
      --panel-2: #10151a;
      --text: #e7edf2;
      --muted: #98a7b3;
      --line: #2b3540;
      --ok: #61d394;
      --warn: #f5c86b;
      --bad: #ff7f7f;
      --info: #74b9ff;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    .shell {
      width: min(1120px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 24px 0 32px;
    }

    header {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 16px;
      align-items: end;
      margin-bottom: 18px;
      border-bottom: 1px solid var(--line);
      padding-bottom: 16px;
    }

    h1 {
      margin: 0;
      font-size: 28px;
      font-weight: 700;
      letter-spacing: 0;
    }

    .subhead {
      color: var(--muted);
      margin-top: 6px;
      font-size: 14px;
    }

    .status-strip {
      display: flex;
      gap: 10px;
      align-items: center;
      justify-content: flex-end;
      flex-wrap: wrap;
    }

    .pill {
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 999px;
      padding: 7px 10px;
      font-size: 13px;
      color: var(--muted);
      white-space: nowrap;
    }

    .grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
    }

    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      min-width: 0;
    }

    .panel h2 {
      margin: 0;
      padding: 13px 14px;
      border-bottom: 1px solid var(--line);
      font-size: 14px;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: var(--muted);
    }

    .rows {
      padding: 8px 14px 12px;
    }

    .row {
      display: grid;
      grid-template-columns: 112px minmax(0, 1fr);
      gap: 12px;
      padding: 9px 0;
      border-bottom: 1px solid rgba(43, 53, 64, 0.65);
      min-height: 38px;
      align-items: center;
    }

    .row:last-child {
      border-bottom: 0;
    }

    .label {
      color: var(--muted);
      font-size: 13px;
    }

    .value {
      font-family: ui-monospace, "SFMono-Regular", Consolas, "Liberation Mono", monospace;
      font-size: 14px;
      overflow-wrap: anywhere;
    }

    .status {
      font-weight: 700;
    }

    .status.OK {
      color: var(--ok);
    }

    .status.QUOTA,
    .status.TIMEOUT,
    .status.NO_KEY,
    .status.AUTH {
      color: var(--warn);
    }

    .status.ERROR,
    .status.OFFLINE,
    .status.REMOTE {
      color: var(--bad);
    }

    .terminal {
      margin-top: 14px;
      background: var(--panel-2);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      overflow: auto;
    }

    pre {
      margin: 0;
      font-family: ui-monospace, "SFMono-Regular", Consolas, "Liberation Mono", monospace;
      font-size: 12px;
      line-height: 1.45;
      color: #dce7ef;
    }

    @media (max-width: 860px) {
      header {
        grid-template-columns: 1fr;
        align-items: start;
      }

      .status-strip {
        justify-content: flex-start;
      }

      .grid {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <main class="shell">
    <header>
      <div>
        <h1>Monad Bridge</h1>
        <div class="subhead">Live read-only telemetry from bridge.py</div>
      </div>
      <div class="status-strip">
        <div class="pill">Refresh <span id="refresh">--</span>s</div>
        <div class="pill">Updated <span id="updated">--</span></div>
      </div>
    </header>

    <section class="grid">
      <article class="panel">
        <h2>Drydock</h2>
        <div class="rows">
          <div class="row"><div class="label">Host OS</div><div class="value" id="os-name">--</div></div>
          <div class="row"><div class="label">Platform</div><div class="value" id="platform">--</div></div>
          <div class="row"><div class="label">Uptime</div><div class="value" id="uptime">--</div></div>
        </div>
      </article>

      <article class="panel">
        <h2>Engine</h2>
        <div class="rows">
          <div class="row"><div class="label">Model</div><div class="value" id="model">--</div></div>
          <div class="row"><div class="label">Connection</div><div class="value status" id="connection">--</div></div>
          <div class="row"><div class="label">Latency</div><div class="value" id="latency">--</div></div>
          <div class="row"><div class="label">Detail</div><div class="value" id="detail">--</div></div>
          <div class="row"><div class="label">Checked</div><div class="value" id="checked">--</div></div>
        </div>
      </article>

      <article class="panel">
        <h2>Chronology</h2>
        <div class="rows">
          <div class="row"><div class="label">Log Files</div><div class="value" id="log-files">--</div></div>
          <div class="row"><div class="label">Entries</div><div class="value" id="log-entries">--</div></div>
          <div class="row"><div class="label">Last Watch</div><div class="value" id="last-watch">--</div></div>
          <div class="row"><div class="label">Source</div><div class="value" id="source">--</div></div>
        </div>
      </article>
    </section>

    <section class="terminal">
      <pre id="terminal">Loading bridge telemetry...</pre>
    </section>
  </main>

  <script>
    const ids = {
      refresh: document.getElementById("refresh"),
      updated: document.getElementById("updated"),
      osName: document.getElementById("os-name"),
      platform: document.getElementById("platform"),
      uptime: document.getElementById("uptime"),
      model: document.getElementById("model"),
      connection: document.getElementById("connection"),
      latency: document.getElementById("latency"),
      detail: document.getElementById("detail"),
      checked: document.getElementById("checked"),
      logFiles: document.getElementById("log-files"),
      logEntries: document.getElementById("log-entries"),
      lastWatch: document.getElementById("last-watch"),
      source: document.getElementById("source"),
      terminal: document.getElementById("terminal")
    };

    let refreshMs = 5000;

    function text(value, fallback = "--") {
      return value === null || value === undefined || value === "" ? fallback : String(value);
    }

    function applyStatus(status) {
      ids.connection.className = "value status " + text(status);
      ids.connection.textContent = text(status);
    }

    async function loadTelemetry() {
      try {
        const response = await fetch("/api/status", { cache: "no-store" });
        if (!response.ok) throw new Error("HTTP " + response.status);
        const data = await response.json();

        refreshMs = Math.max(1000, Number(data.refresh_seconds || 5) * 1000);
        ids.refresh.textContent = text(data.refresh_seconds);
        ids.updated.textContent = text(data.generated_at_local || data.generated_at_utc);
        ids.osName.textContent = text(data.drydock.os);
        ids.platform.textContent = text(data.drydock.platform);
        ids.uptime.textContent = text(data.drydock.uptime);
        ids.model.textContent = text(data.engine.model);
        applyStatus(data.engine.status);
        ids.latency.textContent = data.engine.latency_ms === null ? "n/a" : data.engine.latency_ms + " ms";
        ids.detail.textContent = text(data.engine.detail);
        ids.checked.textContent = text(data.engine.checked_at_utc, "never");
        ids.logFiles.textContent = text(data.chronology.log_files);
        ids.logEntries.textContent = text(data.chronology.log_entries);
        ids.lastWatch.textContent = text(data.chronology.latest_timestamp_utc, "none");
        ids.source.textContent = text(data.chronology.latest_source);
        ids.terminal.textContent = text(data.terminal);
      } catch (error) {
        applyStatus("ERROR");
        ids.detail.textContent = error.message;
        ids.updated.textContent = "fetch failed";
      } finally {
        window.setTimeout(loadTelemetry, refreshMs);
      }
    }

    loadTelemetry();
  </script>
</body>
</html>
"""


class BridgeState:
    def __init__(self, refresh: float, engine_interval: float, timeout: float, model: str, engine_enabled: bool):
        self.refresh = refresh
        self.model = model
        self.probe = bridge.EngineProbe(
            model=model,
            timeout=timeout,
            interval=max(refresh, engine_interval),
            enabled=engine_enabled,
        )

    def snapshot(self) -> dict:
        os_name, os_detail = bridge.detect_os()
        uptime_seconds = bridge.get_uptime_seconds()
        engine = self.probe.maybe_probe()
        chronology = bridge.scan_chronology()
        generated = bridge.utc_now()

        return {
            "generated_at_utc": format_dt(generated),
            "generated_at_local": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
            "refresh_seconds": self.refresh,
            "drydock": {
                "os": os_name,
                "platform": os_detail,
                "uptime": bridge.format_duration(uptime_seconds),
                "uptime_seconds": uptime_seconds,
            },
            "engine": {
                "model": self.model,
                "status": engine.status,
                "latency_ms": engine.latency_ms,
                "detail": engine.detail,
                "checked_at_utc": format_dt(engine.checked_at),
            },
            "chronology": {
                "log_files": chronology.log_files,
                "log_entries": chronology.log_entries,
                "latest_timestamp_utc": format_dt(chronology.latest_timestamp),
                "latest_source": chronology.latest_source,
            },
            "terminal": bridge.render_dashboard(engine, chronology, self.refresh, self.model),
        }


def format_dt(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def make_handler(state: BridgeState):
    class BridgeHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            route = urlparse(self.path).path
            if route == "/":
                self.send_text(HTML, "text/html; charset=utf-8")
                return
            if route == "/api/status":
                self.send_json(state.snapshot())
                return
            if route == "/health":
                self.send_json({"ok": True})
                return
            self.send_error(404, "Not found")

        def send_json(self, payload: dict):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def send_text(self, payload: str, content_type: str):
            body = payload.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args):
            timestamp = time.strftime("%H:%M:%S")
            sys.stderr.write(f"[{timestamp}] {self.address_string()} {format % args}\n")

    return BridgeHandler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Monad Bridge web dashboard.")
    parser.add_argument("--host", default=DEFAULT_HOST, help="host interface to bind")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="port to bind")
    parser.add_argument("--refresh", type=float, default=DEFAULT_REFRESH, help="browser refresh interval in seconds")
    parser.add_argument("--engine-interval", type=float, default=DEFAULT_ENGINE_INTERVAL, help="Gemini probe interval in seconds")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="Gemini probe timeout in seconds")
    parser.add_argument("--model", default=bridge.DEFAULT_MODEL, help="Gemini model to probe")
    parser.add_argument("--no-engine", action="store_true", help="disable Gemini API probing")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    state = BridgeState(
        refresh=max(1.0, args.refresh),
        engine_interval=max(1.0, args.engine_interval),
        timeout=max(0.5, args.timeout),
        model=args.model,
        engine_enabled=not args.no_engine,
    )
    server = ThreadingHTTPServer((args.host, args.port), make_handler(state))
    print(f"Monad Bridge web dashboard: http://{args.host}:{args.port}/")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBridge web dashboard offline.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
