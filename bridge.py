import argparse
import ctypes
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / "logs"
CANONICAL_LOG = ROOT / "helmsman_v2.log"
DEFAULT_MODEL = "gemini-2.5-flash"
ISO_RE = re.compile(r"\d{4}-\d{2}-\d{2}[T ][0-9:.]+(?:Z|[+-]\d{2}:?\d{2})?")


@dataclass
class EngineStatus:
    status: str = "PENDING"
    latency_ms: int | None = None
    detail: str = "not checked yet"
    checked_at: datetime | None = None


@dataclass
class ChronologyStatus:
    log_files: int
    log_entries: int
    latest_timestamp: datetime | None
    latest_source: str


class EngineProbe:
    def __init__(self, model: str, timeout: float, interval: float, enabled: bool):
        self.model = model
        self.timeout = timeout
        self.interval = interval
        self.enabled = enabled
        self.last_probe_monotonic = 0.0
        self.status = EngineStatus(status="DISABLED" if not enabled else "PENDING")

    def maybe_probe(self) -> EngineStatus:
        if not self.enabled:
            return self.status
        now = time.monotonic()
        if self.status.checked_at and now - self.last_probe_monotonic < self.interval:
            return self.status
        self.last_probe_monotonic = now
        self.status = self._probe()
        return self.status

    def _probe(self) -> EngineStatus:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return EngineStatus(status="NO_KEY", detail="GEMINI_API_KEY is not set", checked_at=utc_now())

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}?key={api_key}"
        request = urllib.request.Request(url, method="GET")
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                response.read(256)
                latency = int((time.perf_counter() - started) * 1000)
                return EngineStatus(status="OK", latency_ms=latency, detail=f"HTTP {response.status}", checked_at=utc_now())
        except TimeoutError:
            latency = int((time.perf_counter() - started) * 1000)
            return EngineStatus(status="TIMEOUT", latency_ms=latency, detail=f"> {self.timeout:.1f}s", checked_at=utc_now())
        except urllib.error.HTTPError as exc:
            latency = int((time.perf_counter() - started) * 1000)
            body = safe_read_error(exc)
            status = classify_http_error(exc.code, body)
            return EngineStatus(status=status, latency_ms=latency, detail=f"HTTP {exc.code}", checked_at=utc_now())
        except urllib.error.URLError as exc:
            latency = int((time.perf_counter() - started) * 1000)
            reason = str(getattr(exc, "reason", exc))
            return EngineStatus(status="OFFLINE", latency_ms=latency, detail=trim(reason, 42), checked_at=utc_now())
        except Exception as exc:
            latency = int((time.perf_counter() - started) * 1000)
            return EngineStatus(status="ERROR", latency_ms=latency, detail=trim(str(exc), 42), checked_at=utc_now())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def safe_read_error(exc: urllib.error.HTTPError) -> str:
    try:
        return exc.read().decode("utf-8", errors="replace")
    except Exception:
        return ""


def classify_http_error(code: int, body: str) -> str:
    text = body.lower()
    if code == 429 or "quota" in text or "resource_exhausted" in text:
        return "QUOTA"
    if code in (401, 403):
        return "AUTH"
    if code >= 500:
        return "REMOTE"
    return "ERROR"


def detect_os() -> tuple[str, str]:
    system = platform.system()
    detail = platform.platform()
    if system == "Linux":
        os_release = Path("/etc/os-release")
        if os_release.exists():
            text = os_release.read_text(encoding="utf-8", errors="replace")
            pretty = find_os_release_value(text, "PRETTY_NAME")
            if pretty:
                detail = pretty
                if "kubuntu" in pretty.lower():
                    return "Kubuntu", detail
        return "Linux", detail
    if system == "Windows":
        return "Windows", detail
    if system == "Darwin":
        return "macOS", detail
    return system or "Unknown", detail


def find_os_release_value(text: str, key: str) -> str | None:
    for line in text.splitlines():
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip().strip('"')
    return None


def get_uptime_seconds() -> int | None:
    system = platform.system()
    try:
        if system == "Windows":
            return int(ctypes.windll.kernel32.GetTickCount64() // 1000)
        if system == "Linux":
            return int(float(Path("/proc/uptime").read_text().split()[0]))
        if system == "Darwin":
            output = subprocess.check_output(["sysctl", "-n", "kern.boottime"], text=True, timeout=2)
            match = re.search(r"sec = (\d+)", output)
            if match:
                return int(time.time()) - int(match.group(1))
    except Exception:
        return None
    return None


def format_duration(seconds: int | None) -> str:
    if seconds is None:
        return "unknown"
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    if days:
        return f"{days}d {hours}h {minutes}m"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def scan_chronology() -> ChronologyStatus:
    files: list[Path] = []
    if LOG_DIR.exists():
        files.extend(path for path in LOG_DIR.rglob("*") if path.is_file())
    if CANONICAL_LOG.exists():
        files.append(CANONICAL_LOG)

    total_entries = 0
    latest_timestamp: datetime | None = None
    latest_source = "none"

    for path in files:
        file_entries, file_latest = inspect_log_file(path)
        total_entries += file_entries
        fallback = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        candidate = file_latest or fallback
        if latest_timestamp is None or candidate > latest_timestamp:
            latest_timestamp = candidate
            latest_source = str(path.relative_to(ROOT))

    return ChronologyStatus(
        log_files=len(files),
        log_entries=total_entries,
        latest_timestamp=latest_timestamp,
        latest_source=latest_source,
    )


def inspect_log_file(path: Path) -> tuple[int, datetime | None]:
    entries = 0
    latest: datetime | None = None
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                entries += 1
                parsed = parse_timestamp_from_line(stripped)
                if parsed and (latest is None or parsed > latest):
                    latest = parsed
    except Exception:
        return 0, None
    return entries, latest


def parse_timestamp_from_line(line: str) -> datetime | None:
    try:
        if line.startswith("{"):
            value = json.loads(line).get("timestamp")
            parsed = parse_datetime(value) if value else None
            if parsed:
                return parsed
    except Exception:
        pass

    match = ISO_RE.search(line)
    if match:
        return parse_datetime(match.group(0))
    return None


def parse_datetime(value: str) -> datetime | None:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    if re.search(r"[+-]\d{4}$", text):
        text = text[:-5] + text[-5:-2] + ":" + text[-2:]
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def render_dashboard(engine: EngineStatus, chronology: ChronologyStatus, refresh: float, model: str) -> str:
    os_name, os_detail = detect_os()
    uptime = format_duration(get_uptime_seconds())
    now = utc_now().strftime("%Y-%m-%d %H:%M:%S UTC")
    width = max(72, min(shutil.get_terminal_size((100, 30)).columns, 120))

    latest = chronology.latest_timestamp.strftime("%Y-%m-%d %H:%M:%S UTC") if chronology.latest_timestamp else "none"
    latency = f"{engine.latency_ms} ms" if engine.latency_ms is not None else "n/a"
    checked = engine.checked_at.strftime("%H:%M:%S UTC") if engine.checked_at else "never"

    lines = [
        rule(width),
        center("MONAD BRIDGE DISPLAY", width),
        center(f"{now} | refresh {refresh:g}s | Ctrl+C to exit", width),
        rule(width),
        section("DRYDOCK", width),
        row("Host OS", os_name, width),
        row("Platform", os_detail, width),
        row("Uptime", uptime, width),
        rule(width),
        section("ENGINE", width),
        row("Gemini Model", model, width),
        row("Connection", engine.status, width),
        row("Latency", latency, width),
        row("Detail", engine.detail, width),
        row("Checked", checked, width),
        rule(width),
        section("CHRONOLOGY", width),
        row("Log Files", str(chronology.log_files), width),
        row("Log Entries", str(chronology.log_entries), width),
        row("Last Watch", latest, width),
        row("Source", chronology.latest_source, width),
        rule(width),
    ]
    return "\n".join(lines)


def rule(width: int) -> str:
    return "+" + "-" * (width - 2) + "+"


def center(text: str, width: int) -> str:
    return "|" + trim(text, width - 2).center(width - 2) + "|"


def section(text: str, width: int) -> str:
    label = f" {text} "
    fill = width - len(label) - 2
    return "|" + label + "-" * max(0, fill) + "|"


def row(label: str, value: str, width: int) -> str:
    left = f"  {label:<16}"
    available = width - len(left) - 3
    return "|" + left + trim(str(value), available).ljust(available) + " |"


def trim(value: str, limit: int) -> str:
    if limit <= 0:
        return ""
    text = str(value).replace("\n", " ")
    if len(text) <= limit:
        return text
    if limit <= 3:
        return text[:limit]
    return text[: limit - 3] + "..."


def clear_screen() -> None:
    sys.stdout.write("\033[2J\033[H")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Monad terminal bridge display.")
    parser.add_argument("--refresh", type=float, default=5.0, help="dashboard redraw interval in seconds")
    parser.add_argument("--engine-interval", type=float, default=60.0, help="Gemini probe interval in seconds")
    parser.add_argument("--timeout", type=float, default=3.0, help="Gemini probe timeout in seconds")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Gemini model to probe")
    parser.add_argument("--no-engine", action="store_true", help="disable Gemini API probing")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    refresh = max(1.0, args.refresh)
    probe = EngineProbe(
        model=args.model,
        timeout=max(0.5, args.timeout),
        interval=max(refresh, args.engine_interval),
        enabled=not args.no_engine,
    )

    try:
        while True:
            engine = probe.maybe_probe()
            chronology = scan_chronology()
            clear_screen()
            sys.stdout.write(render_dashboard(engine, chronology, refresh, args.model))
            sys.stdout.write("\n")
            sys.stdout.flush()
            time.sleep(refresh)
    except KeyboardInterrupt:
        clear_screen()
        print("Bridge display offline.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
