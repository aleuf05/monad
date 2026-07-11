import { useState, useEffect, useRef, useCallback } from "react";
import { Navigation, Crosshair, Anchor } from "lucide-react";

/*
  BRIDGE STATION 2.1
  One world. Two views. One command.

  Design tokens:
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
const TICK_MS = 900;
const MAX_TURN_PER_TICK = 6; // degrees
const ARRIVE_THRESHOLD = 10; // chart units

const initialVessels = [
  { id: "monad", name: "MONAD", isPlayer: true, x: 300, y: 220, course: 250, speed: 12, waypoint: null },
  { id: "amber", name: "PILOT AMBER", isPlayer: false, x: 430, y: 120, course: 205, speed: 8, waypoint: null },
  { id: "gamma", name: "CONVOY GAMMA", isPlayer: false, x: 140, y: 300, course: 40, speed: 5, waypoint: null },
];

function norm360(deg) {
  return ((deg % 360) + 360) % 360;
}

function turnToward(current, target, maxStep) {
  let diff = norm360(target - current);
  if (diff > 180) diff -= 360;
  if (Math.abs(diff) <= maxStep) return norm360(target);
  return norm360(current + Math.sign(diff) * maxStep);
}

function bearingTo(from, to) {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  return norm360((Math.atan2(dx, -dy) * 180) / Math.PI);
}

function rangeNm(from, to) {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  return Math.sqrt(dx * dx + dy * dy) * 0.05;
}

function stepVessel(v) {
  let { x, y, course, speed, waypoint } = v;
  if (waypoint) {
    const targetBearing = bearingTo(v, waypoint);
    course = turnToward(course, targetBearing, MAX_TURN_PER_TICK);
    const dist = Math.sqrt((waypoint.x - x) ** 2 + (waypoint.y - y) ** 2);
    if (dist < ARRIVE_THRESHOLD) {
      return { ...v, x: waypoint.x, y: waypoint.y, waypoint: null, arrived: true };
    }
  }
  const rad = (course * Math.PI) / 180;
  const vx = Math.sin(rad) * (speed * 0.06);
  const vy = -Math.cos(rad) * (speed * 0.06);
  let nx = x + vx;
  let ny = y + vy;
  let nc = course;
  if (nx < 20 || nx > CHART_W - 20) {
    nc = norm360(360 - nc);
    nx = Math.max(20, Math.min(CHART_W - 20, nx));
  }
  if (ny < 20 || ny > CHART_H - 20) {
    nc = norm360(180 - nc);
    ny = Math.max(20, Math.min(CHART_H - 20, ny));
  }
  return { ...v, x: nx, y: ny, course: nc, arrived: false };
}

function fmtTime(t) {
  const h = String(Math.floor(t / 3600) % 24).padStart(2, "0");
  const m = String(Math.floor(t / 60) % 60).padStart(2, "0");
  const s = String(Math.floor(t) % 60).padStart(2, "0");
  return `${h}:${m}:${s}Z`;
}

export default function BridgeStation() {
  const [vessels, setVessels] = useState(initialVessels);
  const [selectedId, setSelectedId] = useState("monad");
  const [waypointMode, setWaypointMode] = useState(false);
  const [log, setLog] = useState([
    { t: 0, text: "Bridge Station online. All instruments nominal." },
  ]);
  const [clock, setClock] = useState(12 * 3600 + 480);
  const [flash, setFlash] = useState(false);
  const logRef = useRef(null);

  const addLog = useCallback((text) => {
    setLog((prev) => [...prev.slice(-7), { t: Date.now(), text }]);
  }, []);

  useEffect(() => {
    const id = setInterval(() => {
      setVessels((prev) => {
        const next = prev.map(stepVessel);
        next.forEach((v, i) => {
          if (v.arrived && !prev[i].arrived) {
            addLog(`${v.name} — waypoint reached, resuming standard patrol.`);
          }
        });
        return next;
      });
      setClock((c) => c + TICK_MS / 200);
    }, TICK_MS);
    return () => clearInterval(id);
  }, [addLog]);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [log]);

  const selected = vessels.find((v) => v.id === selectedId) || null;
  const monad = vessels.find((v) => v.id === "monad");

  const handleSelect = (id) => {
    setWaypointMode(false);
    setSelectedId(id);
    const v = vessels.find((vv) => vv.id === id);
    if (v && id !== "monad") {
      addLog(
        `Selected ${v.name} — bearing ${Math.round(bearingTo(monad, v))}°, range ${rangeNm(monad, v).toFixed(1)} nm.`
      );
    } else if (v) {
      addLog(`Selected MONAD — own ship.`);
    }
  };

  const handleChartClick = (e) => {
    if (!waypointMode) return;
    const svg = e.currentTarget;
    const rect = svg.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * CHART_W;
    const y = ((e.clientY - rect.top) / rect.height) * CHART_H;
    setVessels((prev) =>
      prev.map((v) => (v.id === "monad" ? { ...v, waypoint: { x, y } } : v))
    );
    setWaypointMode(false);
    setFlash(true);
    setTimeout(() => setFlash(false), 600);
    const brg = Math.round(bearingTo(monad, { x, y }));
    addLog(`Waypoint set — bearing ${brg}°. Course changing.`);
  };

  const targetBearing = selected && selected.id !== "monad" ? bearingTo(monad, selected) : null;
  const targetRange = selected && selected.id !== "monad" ? rangeNm(monad, selected) : null;
  const relativeBearing =
    targetBearing !== null ? norm360(targetBearing - monad.course) : null;

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
        <div className="bs-mono" style={styles.watch}>WATCH {fmtTime(clock)}</div>
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

            {/* compass rose */}
            <g transform={`translate(${CHART_W - 46}, 46)`} opacity="0.6">
              <circle r="26" fill="none" stroke="#3A4C68" strokeWidth="1" />
              <text y="-30" textAnchor="middle" className="bs-mono" fontSize="9" fill="#6B7C93">N</text>
            </g>

            {/* waypoint marker + course line */}
            {monad.waypoint && (
              <>
                <line
                  x1={monad.x} y1={monad.y}
                  x2={monad.waypoint.x} y2={monad.waypoint.y}
                  stroke="#E8A33D" strokeWidth="1.5" strokeDasharray="4 3" opacity="0.7"
                />
                <circle cx={monad.waypoint.x} cy={monad.waypoint.y} r="6" fill="none" stroke="#E8A33D" strokeWidth="2" />
              </>
            )}
            {flash && monad.waypoint && (
              <circle
                cx={monad.waypoint.x} cy={monad.waypoint.y} r="6"
                fill="none" stroke="#E8A33D"
                style={{ animation: "waypointPulse 0.6s ease-out" }}
              />
            )}

            {/* vessels */}
            {vessels.map((v) => {
              const isSel = v.id === selectedId;
              const color = v.isPlayer ? "#E8A33D" : "#4FD1C5";
              return (
                <g
                  key={v.id}
                  className="contact-icon"
                  transform={`translate(${v.x},${v.y}) rotate(${v.course})`}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleSelect(v.id);
                  }}
                >
                  {isSel && <circle r="14" fill="none" stroke={color} strokeWidth="1" opacity="0.5" />}
                  <polygon points="0,-9 6,8 0,4 -6,8" fill={color} stroke="#0B1220" strokeWidth="1" />
                </g>
              );
            })}

            {/* labels (unrotated) */}
            {vessels.map((v) => (
              <text
                key={v.id + "-label"}
                x={v.x} y={v.y - 16}
                textAnchor="middle"
                className="bs-mono"
                fontSize="9"
                fill={v.id === selectedId ? "#DCE6F2" : "#6B7C93"}
              >
                {v.name}
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

            {selected && selected.id !== "monad" ? (
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

            {selected && selected.id !== "monad" && (
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
              <div className="bs-display" style={styles.actionName}>{selected.name}</div>
              <div className="bs-mono" style={styles.actionStats}>
                {selected.id === "monad" ? (
                  <>COURSE {String(Math.round(selected.course)).padStart(3, "0")}° · SPEED {selected.speed} KT</>
                ) : (
                  <>RANGE {targetRange.toFixed(1)} NM · BEARING {String(Math.round(targetBearing)).padStart(3, "0")}°</>
                )}
              </div>
            </div>
            {selected.id === "monad" ? (
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
  watch: { fontSize: 12, color: "#6B7C93", letterSpacing: "0.05em" },
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
