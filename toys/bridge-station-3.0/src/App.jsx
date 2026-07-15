import { useState, useEffect, useRef, useCallback } from "react";
import { Navigation, Crosshair, Anchor } from "lucide-react";

/*
  BRIDGE STATION 3.0
  One world. Two views. One command. Now against the real world:
  2.1's operator loop (Select -> Act -> World changes -> Instruments
  respond), wired to fleetcore-serve instead of mock in-memory state.
  "Act" here is real: Set Waypoint sends an actual set-route Command over
  the WebSocket, and every panel re-renders from the snapshot the server
  broadcasts back -- there is no local physics simulation left in this
  file at all, unlike 2.1.

  Design tokens (unchanged from 2.1):
  - bg base:      #0B1220 (deep navy, not pure black)
  - panel:        #111A2B
  - grid line:    #1E2C42
  - amber (Fleet Motion / own-ship data): #E8A33D
  - teal (Periscope / target data):       #4FD1C5
  - text primary: #DCE6F2
  - text muted:   #6B7C93
  - display face: "Oswald" (condensed, stencil / signage feel)
  - data face:    "JetBrains Mono" (instrument readouts)
*/

const CHART_W = 600;
const CHART_H = 400;
const MARGIN = 40;

const { bearingDegrees, distanceKm, normalizeDegrees } = window.MonadFleetState.utils;

// Command authority is granted by the server per-connection, the same for
// everyone -- there is no client-supplied token anymore (see
// fleetcore-control's app.js comment for why the token field was removed
// everywhere).
function serverUrl() {
  const params = new URLSearchParams(window.location.search);
  return params.get("server") || "wss://cameronlampley.com/fleetcore-ws/ws";
}

function norm360(deg) {
  return ((deg % 360) + 360) % 360;
}

// fleetcore-serve's speed_mps is the vessel's rated/commanded speed, not its
// instantaneous velocity -- it's never reset to 0 on arrival (there's no
// set-speed Command). A vessel only actually has way on while "underway" or
// "transiting"; "arrived", "holding", and "paused" mean it's stationary
// regardless of what speed_mps says.
function actualSpeedMps(vessel) {
  return vessel.status === "underway" || vessel.status === "transiting" ? vessel.speed_mps : 0;
}

function shortestDelta(from, to) {
  let delta = norm360(to) - norm360(from);
  if (delta > 180) delta -= 360;
  if (delta < -180) delta += 360;
  return delta;
}

// Real lat/lng <-> abstract 600x400 chart space, frozen from the first
// snapshot's fleet spread (same "don't rescale the view every tick" call
// toys/bridge-2 makes with its hasCenteredMap flag) rather than recomputed
// every tick, which would make the whole chart jump/rescale as MONAD moves.
function computeBounds(vessels) {
  const lats = vessels.map((v) => v.position.lat);
  const lngs = vessels.map((v) => v.position.lng);
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLng = Math.min(...lngs);
  const maxLng = Math.max(...lngs);
  const latSpan = Math.max(maxLat - minLat, 0.05);
  const lngSpan = Math.max(maxLng - minLng, 0.05);
  const pad = 0.6;
  return {
    minLat: minLat - latSpan * pad,
    maxLat: maxLat + latSpan * pad,
    minLng: minLng - lngSpan * pad,
    maxLng: maxLng + lngSpan * pad,
  };
}

function toChart(bounds, position) {
  const { minLat, maxLat, minLng, maxLng } = bounds;
  const x = MARGIN + ((position.lng - minLng) / (maxLng - minLng)) * (CHART_W - MARGIN * 2);
  const y = MARGIN + ((maxLat - position.lat) / (maxLat - minLat)) * (CHART_H - MARGIN * 2);
  return { x, y };
}

// Two vessels close together on the chart (e.g. holding station near each
// other) otherwise render their callsign labels on top of one another,
// illegible. Nudges each label's default position (point.y - 16) down in
// 12px steps until it clears every label already placed this pass.
function layoutLabelPositions(vessels, bounds) {
  const placed = [];
  return vessels.map((v) => {
    const point = toChart(bounds, v.position);
    const width = Math.max(v.callsign.length * 5.5, 20);
    let y = point.y - 16;
    for (let attempt = 0; attempt < 6; attempt++) {
      const collides = placed.some(
        (p) => Math.abs(p.x - point.x) < (p.width + width) / 2 && Math.abs(p.y - y) < 11
      );
      if (!collides) break;
      y += 12;
    }
    placed.push({ x: point.x, y, width });
    return { id: v.id, x: point.x, y, callsign: v.callsign };
  });
}

function toGeo(bounds, point) {
  const { minLat, maxLat, minLng, maxLng } = bounds;
  const lng = minLng + ((point.x - MARGIN) / (CHART_W - MARGIN * 2)) * (maxLng - minLng);
  const lat = maxLat - ((point.y - MARGIN) / (CHART_H - MARGIN * 2)) * (maxLat - minLat);
  return { lat, lng };
}

function fmtSimTime(isoString) {
  if (!isoString) return "--:--:--Z";
  const d = new Date(isoString);
  if (Number.isNaN(d.getTime())) return "--:--:--Z";
  const h = String(d.getUTCHours()).padStart(2, "0");
  const m = String(d.getUTCMinutes()).padStart(2, "0");
  const s = String(d.getUTCSeconds()).padStart(2, "0");
  return `${h}:${m}:${s}Z`;
}

export default function BridgeStation() {
  const [snapshot, setSnapshot] = useState(null);
  const [bounds, setBounds] = useState(null);
  const [linkStatus, setLinkStatus] = useState("Connecting…");
  const [selectedId, setSelectedId] = useState(null);
  const [waypointMode, setWaypointMode] = useState(false);
  const [log, setLog] = useState([
    { t: 0, text: "Bridge Station online. Awaiting live world…" },
  ]);
  const [flash, setFlash] = useState(false);
  const logRef = useRef(null);
  const socketRef = useRef(null);
  const reconnectDelayRef = useRef(1000);
  const reconnectTimerRef = useRef(null);
  const hasLoggedLiveRef = useRef(false);

  const addLog = useCallback((text) => {
    setLog((prev) => [...prev.slice(-7), { t: Date.now(), text }]);
  }, []);

  useEffect(() => {
    function connect() {
      clearTimeout(reconnectTimerRef.current);
      setLinkStatus("Connecting…");
      const socket = new WebSocket(serverUrl());
      socketRef.current = socket;

      socket.addEventListener("open", () => {
        setLinkStatus("Live");
        reconnectDelayRef.current = 1000;
      });

      socket.addEventListener("message", (event) => {
        let message;
        try {
          message = JSON.parse(event.data);
        } catch {
          return;
        }
        if (message.type === "snapshot") {
          setSnapshot(message.snapshot);
          setBounds((prev) => prev || computeBounds(message.snapshot.vessels));
          if (!hasLoggedLiveRef.current) {
            hasLoggedLiveRef.current = true;
            addLog("Live world acquired. All instruments nominal.");
          }
        } else if (message.type === "error") {
          addLog(`Command rejected — ${message.message}`);
        }
      });

      socket.addEventListener("close", () => {
        setLinkStatus("Reconnecting…");
        reconnectTimerRef.current = setTimeout(() => {
          reconnectDelayRef.current = Math.min(reconnectDelayRef.current * 1.6, 15000);
          connect();
        }, reconnectDelayRef.current);
      });

      socket.addEventListener("error", () => setLinkStatus("Connection error"));
    }
    connect();
    return () => {
      clearTimeout(reconnectTimerRef.current);
      socketRef.current?.close();
    };
  }, [addLog]);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [log]);

  const vessels = snapshot?.vessels || [];
  const flagship = vessels.find((v) => v.kind === "flagship") || null;
  const selected = vessels.find((v) => v.id === selectedId) || null;

  const handleSelect = (vessel) => {
    setWaypointMode(false);
    setSelectedId(vessel.id);
    if (flagship && vessel.id !== flagship.id) {
      const brg = bearingDegrees(flagship.position, vessel.position);
      const rng = distanceKm(flagship.position, vessel.position) * 0.539957;
      addLog(`Selected ${vessel.callsign} — bearing ${Math.round(brg)}°, range ${rng.toFixed(1)} nm.`);
    } else {
      addLog(`Selected ${vessel.callsign} — own ship.`);
    }
  };

  const handleChartClick = (e) => {
    if (!waypointMode || !bounds || !flagship || !socketRef.current) return;
    const svg = e.currentTarget;
    const rect = svg.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * CHART_W;
    const y = ((e.clientY - rect.top) / rect.height) * CHART_H;
    const geo = toGeo(bounds, { x, y });
    socketRef.current.send(
      JSON.stringify({
        type: "set-route",
        vessel_id: flagship.id,
        route: [{ lat: geo.lat, lng: geo.lng }],
      })
    );
    setWaypointMode(false);
    setFlash(true);
    setTimeout(() => setFlash(false), 600);
    const brg = Math.round(bearingDegrees(flagship.position, geo));
    addLog(`Waypoint command sent — bearing ${brg}°. Awaiting world response.`);
  };

  const targetBearing =
    selected && flagship && selected.id !== flagship.id
      ? bearingDegrees(flagship.position, selected.position)
      : null;
  const targetRange =
    selected && flagship && selected.id !== flagship.id
      ? distanceKm(flagship.position, selected.position) * 0.539957
      : null;
  const relativeBearing =
    targetBearing !== null && flagship ? norm360(targetBearing - flagship.course) : null;

  const waypointChart =
    bounds && flagship && flagship.route && flagship.route.length
      ? toChart(bounds, flagship.route[0])
      : null;
  const flagshipChart = bounds && flagship ? toChart(bounds, flagship.position) : null;

  return (
    <div style={styles.root}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
        * { box-sizing: border-box; }
        .bs-mono { font-family: 'JetBrains Mono', monospace; }
        .bs-display { font-family: 'Oswald', sans-serif; }
        .contact-icon { cursor: pointer; transition: filter 120ms ease; }
        .contact-icon:hover { filter: brightness(1.4); }
        .cmd-btn {
          background: #E8A33D; color: #0B1220; border: none; border-radius: 3px;
          font-family: 'Oswald', sans-serif; font-weight: 600; letter-spacing: 0.06em;
          text-transform: uppercase; font-size: 13px; padding: 10px 18px; cursor: pointer;
          transition: background 120ms ease, transform 120ms ease;
        }
        .cmd-btn:hover { background: #F5B85A; transform: translateY(-1px); }
        .cmd-btn.active { background: #4FD1C5; }
        .live-dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: #6B7C93; margin-right: 6px; }
        .live-dot.is-live { background: #4FD1C5; animation: liveBreath 2.2s ease-in-out infinite; }
        @keyframes liveBreath { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        @keyframes waypointPulse {
          0% { stroke-opacity: 1; stroke-width: 3; }
          100% { stroke-opacity: 0; stroke-width: 10; }
        }
        @media (max-width: 860px) {
          .bs-main { grid-template-columns: 1fr !important; }
        }
      `}</style>

      {/* Top status bar */}
      <div style={styles.topbar}>
        <div style={styles.topbarLeft}>
          <Anchor size={16} color="#E8A33D" />
          <span className="bs-display" style={styles.title}>BRIDGE STATION</span>
          <span className="bs-mono" style={styles.subtitle}>· MONAD</span>
        </div>
        <div className="bs-mono" style={styles.watch}>
          <span className={`live-dot ${linkStatus === "Live" ? "is-live" : ""}`} />
          {linkStatus === "Live" ? `WATCH ${fmtSimTime(snapshot?.sim_time)}` : linkStatus}
        </div>
      </div>

      {/* Main dual view */}
      <div className="bs-main" style={styles.main}>
        {/* FLEET MOTION */}
        <div style={styles.panel}>
          <div style={styles.panelHeader}>
            <Navigation size={13} color="#E8A33D" />
            <span className="bs-display" style={{ ...styles.panelLabel, color: "#E8A33D" }}>
              FLEET MOTION
            </span>
            {waypointMode && (
              <span className="bs-mono" style={styles.waypointHint}>
                click chart to plot waypoint
              </span>
            )}
          </div>
          <svg
            viewBox={`0 0 ${CHART_W} ${CHART_H}`}
            style={{ ...styles.chart, cursor: waypointMode ? "crosshair" : "default" }}
            onClick={handleChartClick}
          >
            <defs>
              <pattern id="grid" width="30" height="30" patternUnits="userSpaceOnUse">
                <path d="M 30 0 L 0 0 0 30" fill="none" stroke="#1E2C42" strokeWidth="1" />
              </pattern>
            </defs>
            <rect width={CHART_W} height={CHART_H} fill="#0D1626" />
            <rect width={CHART_W} height={CHART_H} fill="url(#grid)" />

            {!bounds && (
              <text x={CHART_W / 2} y={CHART_H / 2} textAnchor="middle" className="bs-mono" fontSize="12" fill="#3A4C68">
                Awaiting live world…
              </text>
            )}

            {/* compass rose */}
            <g transform={`translate(${CHART_W - 46}, 46)`} opacity="0.6">
              <circle r="26" fill="none" stroke="#3A4C68" strokeWidth="1" />
              <text y="-30" textAnchor="middle" className="bs-mono" fontSize="9" fill="#6B7C93">N</text>
            </g>

            {/* waypoint marker + course line */}
            {waypointChart && flagshipChart && (
              <>
                <line
                  x1={flagshipChart.x} y1={flagshipChart.y}
                  x2={waypointChart.x} y2={waypointChart.y}
                  stroke="#E8A33D" strokeWidth="1.5" strokeDasharray="4 3" opacity="0.7"
                />
                <circle cx={waypointChart.x} cy={waypointChart.y} r="6" fill="none" stroke="#E8A33D" strokeWidth="2" />
              </>
            )}
            {flash && waypointChart && (
              <circle
                cx={waypointChart.x} cy={waypointChart.y} r="6"
                fill="none" stroke="#E8A33D"
                style={{ animation: "waypointPulse 0.6s ease-out" }}
              />
            )}

            {/* vessels */}
            {bounds && vessels.map((v) => {
              const isSel = v.id === selectedId;
              const isFlagship = v.kind === "flagship";
              const color = isFlagship ? "#E8A33D" : "#4FD1C5";
              const point = toChart(bounds, v.position);
              return (
                <g
                  key={v.id}
                  className="contact-icon"
                  transform={`translate(${point.x},${point.y}) rotate(${v.course})`}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleSelect(v);
                  }}
                >
                  {isSel && <circle r="14" fill="none" stroke={color} strokeWidth="1" opacity="0.5" />}
                  <polygon points="0,-9 6,8 0,4 -6,8" fill={color} stroke="#0B1220" strokeWidth="1" />
                </g>
              );
            })}

            {/* labels (unrotated) */}
            {bounds && layoutLabelPositions(vessels, bounds).map((l) => (
              <text
                key={l.id + "-label"}
                x={l.x} y={l.y}
                textAnchor="middle"
                className="bs-mono"
                fontSize="9"
                fill={l.id === selectedId ? "#DCE6F2" : "#6B7C93"}
              >
                {l.callsign}
              </text>
            ))}
          </svg>
        </div>

        {/* PERISCOPE */}
        <div style={styles.panel}>
          <div style={styles.panelHeader}>
            <Crosshair size={13} color="#4FD1C5" />
            <span className="bs-display" style={{ ...styles.panelLabel, color: "#4FD1C5" }}>
              PERISCOPE
            </span>
          </div>
          <svg viewBox="0 0 600 400" style={styles.chart}>
            <rect width="600" height="400" fill="#0D1626" />
            <line x1="0" y1="240" x2="600" y2="240" stroke="#2A3B54" strokeWidth="1" />
            {[1, 2, 3].map((r) => (
              <ellipse key={r} cx="300" cy="240" rx={r * 90} ry={r * 26} fill="none" stroke="#1E2C42" strokeWidth="1" />
            ))}

            {selected && flagship && selected.id !== flagship.id ? (
              <g
                style={{ transition: "transform 300ms ease" }}
                transform={`translate(${300 + (((relativeBearing + 180) % 360) - 180) * 3}, 236)`}
              >
                <line x1="0" y1="-60" x2="0" y2="60" stroke="#4FD1C5" strokeWidth="1" opacity="0.8" />
                <line x1="-14" y1="0" x2="14" y2="0" stroke="#4FD1C5" strokeWidth="1" opacity="0.8" />
                <circle r="7" fill="#4FD1C5" />
                <rect x="-16" y="-9" width="32" height="10" fill="none" />
              </g>
            ) : (
              <text x="300" y="240" textAnchor="middle" className="bs-mono" fontSize="12" fill="#3A4C68">
                {selected ? "OWN SHIP — NO BEARING" : "NO CONTACT SELECTED"}
              </text>
            )}

            <circle cx="300" cy="240" r="150" fill="none" stroke="#233450" strokeWidth="1" />
            <line x1="300" y1="90" x2="300" y2="390" stroke="#233450" strokeWidth="1" strokeDasharray="2 6" />

            {selected && flagship && selected.id !== flagship.id && (
              <text x="16" y="24" className="bs-mono" fontSize="11" fill="#4FD1C5">
                BRG {String(Math.round(targetBearing)).padStart(3, "0")}° · RNG {targetRange.toFixed(1)} NM
              </text>
            )}
          </svg>
        </div>
      </div>

      {/* Contextual action panel */}
      <div style={styles.actionRow}>
        {selected ? (
          <div style={styles.actionPanel}>
            <div style={styles.actionInfo}>
              <div className="bs-display" style={styles.actionName}>{selected.callsign}</div>
              <div className="bs-mono" style={styles.actionStats}>
                {flagship && selected.id === flagship.id ? (
                  <>COURSE {String(Math.round(selected.course)).padStart(3, "0")}° · SPEED {(actualSpeedMps(selected) * 1.94384).toFixed(1)} KT</>
                ) : (
                  <>RANGE {targetRange.toFixed(1)} NM · BEARING {String(Math.round(targetBearing)).padStart(3, "0")}°</>
                )}
              </div>
            </div>
            {flagship && selected.id === flagship.id ? (
              <button
                className={`cmd-btn ${waypointMode ? "active" : ""}`}
                onClick={() => setWaypointMode((w) => !w)}
              >
                {waypointMode ? "Cancel" : "Set Waypoint"}
              </button>
            ) : (
              <span className="bs-mono" style={styles.observeOnly}>OBSERVE ONLY</span>
            )}
          </div>
        ) : (
          <div style={{ ...styles.actionPanel, opacity: 0.5 }}>
            <span className="bs-mono" style={styles.actionStats}>Select a contact on Fleet Motion.</span>
          </div>
        )}
      </div>

      {/* Log strip */}
      <div ref={logRef} className="bs-mono" style={styles.log}>
        {log.map((entry, i) => (
          <div key={entry.t + "-" + i} style={styles.logLine}>
            <span style={{ color: "#4FD1C5" }}>&gt;</span> {entry.text}
          </div>
        ))}
      </div>
    </div>
  );
}

const styles = {
  root: {
    minHeight: "100vh",
    background: "#0B1220",
    color: "#DCE6F2",
    display: "flex",
    flexDirection: "column",
    fontFamily: "'JetBrains Mono', monospace",
  },
  topbar: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "12px 20px",
    borderBottom: "1px solid #1E2C42",
    background: "#0D1626",
  },
  topbarLeft: { display: "flex", alignItems: "center", gap: 8 },
  title: { fontSize: 15, letterSpacing: "0.12em", fontWeight: 600, color: "#DCE6F2" },
  subtitle: { fontSize: 12, color: "#6B7C93" },
  watch: { fontSize: 12, color: "#6B7C93", letterSpacing: "0.05em", display: "flex", alignItems: "center" },
  main: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: 1,
    background: "#1E2C42",
    flex: "1 1 auto",
    minHeight: 320,
  },
  panel: { background: "#0B1220", display: "flex", flexDirection: "column" },
  panelHeader: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    padding: "10px 14px",
    borderBottom: "1px solid #1E2C42",
  },
  panelLabel: { fontSize: 12, letterSpacing: "0.14em", fontWeight: 500 },
  waypointHint: { marginLeft: "auto", fontSize: 10, color: "#E8A33D", letterSpacing: "0.04em" },
  chart: { width: "100%", height: "100%", display: "block" },
  actionRow: { padding: "10px 14px", background: "#0D1626", borderTop: "1px solid #1E2C42" },
  actionPanel: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    background: "#111A2B",
    border: "1px solid #1E2C42",
    borderRadius: 4,
    padding: "12px 16px",
    maxWidth: 420,
  },
  actionName: { fontSize: 14, letterSpacing: "0.08em", marginBottom: 3 },
  actionStats: { fontSize: 11, color: "#9BB0C8" },
  observeOnly: { fontSize: 10, color: "#3A4C68", letterSpacing: "0.08em" },
  log: {
    height: 96,
    overflowY: "auto",
    padding: "8px 14px",
    background: "#080D16",
    borderTop: "1px solid #1E2C42",
    fontSize: 11,
    color: "#6B7C93",
  },
  logLine: { padding: "2px 0" },
};
