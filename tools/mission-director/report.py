"""Publishes the after-action report for a Mission Director run as three
artifacts at web/missions/<mission_id>/, all regenerated fresh from the
persisted state every time publish() runs:

- mission.json -- the machine record, the full state dict verbatim.
- log.md       -- human-readable evidence log.
- index.html   -- the public artifact: summary, event timeline, final
  state, screenshots, anomalies, outcome. Self-contained, no external
  requests, matching Monad's established palette (see
  toys/bridge-station-3.0/src/App.jsx's own design-tokens comment).
"""
import html
import json
import os
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PHASE_LABELS = {
    "MISSION_INITIALIZED": "Initialized",
    "TRANSIT_UNDERWAY": "Transit Underway",
    "STRAIT_TRANSIT": "Strait Transit",
    "APPROACH_QUACKEN": "Approach",
    "RENDEZVOUS_HOLD": "Rendezvous Hold",
    "MISSION_COMPLETE": "Complete",
    "MISSION_STALLED": "Stalled",
    "MISSION_ABORTED": "Aborted",
    "MISSION_FAILED": "Failed",
}

ANOMALY_KINDS = {"stall", "invalid_state", "abort"}


def _fmt_time(epoch_seconds):
    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def publish(state, ducky_position, snapshot):
    out_dir = os.path.join(REPO_ROOT, "web", "missions", state["mission_id"])
    os.makedirs(out_dir, exist_ok=True)

    _write_json(state, out_dir)
    _write_markdown(state, ducky_position, out_dir)
    _write_html(state, ducky_position, snapshot, out_dir)


def _write_json(state, out_dir):
    with open(os.path.join(out_dir, "mission.json"), "w") as f:
        json.dump(state, f, indent=2)
        f.write("\n")


def _write_markdown(state, ducky_position, out_dir):
    lines = [
        f"# Mission {state['mission_id']}",
        "",
        f"**Phase:** {state['phase']} ({PHASE_LABELS.get(state['phase'], state['phase'])})",
        f"**Outcome:** {state['outcome'] or 'in progress'}",
        f"**Rendezvous target:** {ducky_position['lat']}, {ducky_position['lng']}",
        f"**Updated:** {_fmt_time(state['updated_at'])}",
        "",
        "## Evidence Log",
        "",
    ]
    for entry in state["evidence"]:
        stamp = _fmt_time(entry["at"])
        tick = f" (tick {entry['tick']})" if "tick" in entry else ""
        lines.append(f"- `{stamp}`{tick} **[{entry['kind']}]** {entry['detail']}")
    lines.append("")
    lines.append("## Captures")
    lines.append("")
    if not state["captures"]:
        lines.append("None requested.")
    for capture in state["captures"]:
        status = capture["attachment"] or "*(not yet attached)*"
        lines.append(f"- #{capture['id']} — {capture['event']} ({capture['recommended_view']}): {capture['caption']} — {status}")
    with open(os.path.join(out_dir, "log.md"), "w") as f:
        f.write("\n".join(lines) + "\n")


def _write_html(state, ducky_position, snapshot, out_dir):
    phase = state["phase"]
    outcome = state["outcome"]
    is_terminal = phase in ("MISSION_COMPLETE", "MISSION_ABORTED", "MISSION_FAILED")
    verdict_class = {
        "success": "verdict-good", "aborted": "verdict-warn", "failed": "verdict-bad",
    }.get(outcome, "verdict-pending")
    verdict_text = {
        "success": "Mission Complete", "aborted": "Mission Aborted", "failed": "Mission Failed",
    }.get(outcome, PHASE_LABELS.get(phase, phase))

    anomalies = [e for e in state["evidence"] if e["kind"] in ANOMALY_KINDS]

    timeline_rows = "\n".join(
        f'<li class="event event-{html.escape(e["kind"])}">'
        f'<span class="event-time">{html.escape(_fmt_time(e["at"]))}</span>'
        f'<span class="event-kind">{html.escape(e["kind"])}</span>'
        f'<span class="event-detail">{html.escape(e["detail"])}</span>'
        f"</li>"
        for e in state["evidence"]
    )

    capture_cards = "\n".join(_capture_card(c) for c in state["captures"]) or '<p class="empty-note">No captures requested.</p>'

    anomaly_list = (
        "\n".join(f'<li>{html.escape(_fmt_time(a["at"]))} — {html.escape(a["detail"])}</li>' for a in anomalies)
        if anomalies else '<li class="empty-note">None recorded.</li>'
    )

    vessel = next((v for v in snapshot["vessels"] if v["id"] == "vessel.monad"), None)
    final_state_rows = ""
    if vessel:
        final_state_rows = f"""
        <div class="stat"><span class="label">Position</span><span class="value mono">{vessel['position']['lat']:.4f}, {vessel['position']['lng']:.4f}</span></div>
        <div class="stat"><span class="label">Status</span><span class="value mono">{html.escape(vessel['status'])}</span></div>
        <div class="stat"><span class="label">Course</span><span class="value mono">{vessel['course']:.1f}&deg;</span></div>
        <div class="stat"><span class="label">Tick</span><span class="value mono">{snapshot['tick']}</span></div>
        """

    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Mission {html.escape(state['mission_id'])} — After-Action Report</title>
<style>
  :root {{
    --bg: #0B1220; --panel: #111A2B; --panel-2: #0E1626; --line: #1E2C42;
    --amber: #E8A33D; --teal: #4FD1C5; --text: #DCE6F2; --muted: #6B7C93;
    --good: #4FD1C5; --warn: #E8A33D; --bad: #E86A5C;
  }}
  :root[data-theme="light"] {{
    --bg: #EEF2F1; --panel: #FFFFFF; --panel-2: #F5F8F7; --line: #D6E0DE;
    --amber: #B5761E; --teal: #0E8A7D; --text: #10201D; --muted: #5A6B68;
    --good: #0E8A7D; --warn: #B5761E; --bad: #B0362A;
  }}
  @media (prefers-color-scheme: light) {{
    :root:not([data-theme="dark"]) {{
      --bg: #EEF2F1; --panel: #FFFFFF; --panel-2: #F5F8F7; --line: #D6E0DE;
      --amber: #B5761E; --teal: #0E8A7D; --text: #10201D; --muted: #5A6B68;
      --good: #0E8A7D; --warn: #B5761E; --bad: #B0362A;
    }}
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; background: var(--bg); color: var(--text); font-family: 'Segoe UI', Arial, sans-serif; }}
  body {{ padding: 32px 20px 80px; display: flex; justify-content: center; }}
  main {{ width: 100%; max-width: 880px; }}
  .mono {{ font-family: ui-monospace, "JetBrains Mono", "SF Mono", Consolas, monospace; font-variant-numeric: tabular-nums; }}
  .eyebrow {{ font-size: 0.68rem; font-weight: 800; letter-spacing: 0.16em; text-transform: uppercase; color: var(--muted); margin: 0; }}
  h1 {{ margin: 6px 0 0; font-size: clamp(1.5rem, 4vw, 2rem); text-wrap: balance; }}
  header {{ display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; padding-bottom: 20px; margin-bottom: 24px; border-bottom: 1px solid var(--line); flex-wrap: wrap; }}
  .verdict {{ flex: 0 0 auto; padding: 8px 16px; border-radius: 999px; font-size: 0.78rem; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; white-space: nowrap; }}
  .verdict-good {{ color: var(--good); background: rgba(79,209,197,0.12); border: 1px solid rgba(79,209,197,0.4); }}
  .verdict-warn {{ color: var(--warn); background: rgba(232,163,61,0.12); border: 1px solid rgba(232,163,61,0.4); }}
  .verdict-bad {{ color: var(--bad); background: rgba(232,106,92,0.12); border: 1px solid rgba(232,106,92,0.4); }}
  .verdict-pending {{ color: var(--muted); background: rgba(107,124,147,0.12); border: 1px solid rgba(107,124,147,0.4); }}
  .section-title {{ display: flex; align-items: baseline; gap: 10px; margin: 32px 0 14px; }}
  .section-title .rule {{ flex: 1; height: 1px; background: var(--line); }}
  .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 1px; background: var(--line); border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }}
  .stat {{ background: var(--panel); padding: 14px 16px; display: flex; flex-direction: column; gap: 4px; }}
  .stat .label {{ font-size: 0.66rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); }}
  .stat .value {{ font-size: 1rem; font-weight: 700; }}
  ul.timeline {{ list-style: none; margin: 0; padding: 0; background: var(--panel-2); border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }}
  .event {{ display: grid; grid-template-columns: 170px 130px 1fr; gap: 12px; padding: 9px 16px; font-size: 0.84rem; border-bottom: 1px solid rgba(30,44,66,0.5); align-items: baseline; }}
  .event:last-child {{ border-bottom: none; }}
  .event-time {{ color: var(--muted); font-family: ui-monospace, monospace; font-size: 0.76rem; }}
  .event-kind {{ color: var(--teal); font-weight: 700; text-transform: uppercase; font-size: 0.7rem; letter-spacing: 0.04em; }}
  .event-phase_transition .event-kind {{ color: var(--amber); }}
  .event-stall .event-kind, .event-invalid_state .event-kind, .event-abort .event-kind {{ color: var(--bad); }}
  .captures {{ display: grid; gap: 12px; }}
  .capture-card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 14px 18px; }}
  .capture-card img {{ display: block; max-width: 100%; border-radius: 6px; margin-top: 10px; border: 1px solid var(--line); }}
  .capture-card .meta {{ font-size: 0.78rem; color: var(--muted); margin-top: 4px; }}
  .capture-pending {{ font-size: 0.8rem; color: var(--muted); font-style: italic; }}
  ul.anomalies {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 12px 20px; font-size: 0.86rem; }}
  .empty-note {{ color: var(--muted); font-style: italic; }}
  footer {{ margin-top: 40px; padding-top: 18px; border-top: 1px solid var(--line); color: var(--muted); font-size: 0.74rem; display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px; }}
</style>
</head>
<body>
<main>
  <header>
    <div>
      <p class="eyebrow">Monad &middot; Mission Director</p>
      <h1>{html.escape(state['mission_id'])}</h1>
    </div>
    <span class="verdict {verdict_class}">{html.escape(verdict_text)}</span>
  </header>

  <div class="stats">
    <div class="stat"><span class="label">Phase</span><span class="value mono">{html.escape(phase)}</span></div>
    <div class="stat"><span class="label">Started</span><span class="value mono">{_fmt_time(state['created_at'])}</span></div>
    <div class="stat"><span class="label">Updated</span><span class="value mono">{_fmt_time(state['updated_at'])}</span></div>
    <div class="stat"><span class="label">Evidence</span><span class="value mono">{len(state['evidence'])}</span></div>
    {final_state_rows}
  </div>

  <div class="section-title"><span class="eyebrow">Event Timeline</span><span class="rule"></span></div>
  <ul class="timeline">
    {timeline_rows or '<li class="event"><span class="event-detail empty-note">No evidence recorded yet.</span></li>'}
  </ul>

  <div class="section-title"><span class="eyebrow">Screenshots</span><span class="rule"></span></div>
  <div class="captures">
    {capture_cards}
  </div>

  <div class="section-title"><span class="eyebrow">Anomalies</span><span class="rule"></span></div>
  <ul class="anomalies">
    {anomaly_list}
  </ul>

  <footer>
    <span>MONAD &middot; MISSION DIRECTOR</span>
    <span class="mono">{html.escape(state['mission_id'])}</span>
  </footer>
</main>
</body>
</html>
"""
    with open(os.path.join(out_dir, "index.html"), "w") as f:
        f.write(doc)


def _capture_card(capture):
    if capture["attachment"]:
        media = f'<img src="{html.escape(capture["attachment"])}" alt="{html.escape(capture["caption"])}">'
    else:
        media = '<p class="capture-pending">Awaiting manual attachment.</p>'
    return f"""<div class="capture-card">
      <strong>#{capture['id']} — {html.escape(capture['event'])}</strong>
      <div class="meta">recommended view: {html.escape(capture['recommended_view'])}</div>
      <div>{html.escape(capture['caption'])}</div>
      {media}
    </div>"""
