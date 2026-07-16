import { useState, useEffect, useRef, useCallback } from "react";
import { Navigation, Crosshair, Anchor, Radio, Terminal, SlidersHorizontal } from "lucide-react";

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

// Same id-uniqueness trick as fleetcore-control's idSuffix() -- not
// cryptographically unique, just unique enough that two clicks in the same
// millisecond don't collide.
function idSuffix() {
  return `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
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
  const [activeTab, setActiveTab] = useState("bridge");
  const [commandAuthority, setCommandAuthority] = useState(false);
  const logRef = useRef(null);
  const socketRef = useRef(null);
  const reconnectDelayRef = useRef(1000);
  const reconnectTimerRef = useRef(null);
  const hasLoggedLiveRef = useRef(false);

  const addLog = useCallback((text) => {
    setLog((prev) => [...prev.slice(-7), { t: Date.now(), text }]);
  }, []);

  // Shared by both the chart click-to-waypoint flow and the Control tab --
  // every command is a plain object over the same open socket, same as
  // fleetcore-control's sendCommand().
  const sendCommand = useCallback(
    (command) => {
      if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
        addLog("Command not sent — link is not live.");
        return;
      }
      socketRef.current.send(JSON.stringify(command));
    },
    [addLog]
  );

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
        if (message.type === "connected") {
          setCommandAuthority(Boolean(message.command_authority));
        } else if (message.type === "snapshot") {
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

  // Mission Record rail -- carried over from old Bridge's side rail
  // (toys/bridge/app.js's refreshMissionRail()), dropped during the
  // BRIDGE3-CONSOLIDATE-01 tab-fold since it wasn't in that packet's
  // explicit scope. Persistent across every tab, same as the old rail was
  // visible regardless of which station tab was active.
  const [missionRail, setMissionRail] = useState({
    objective: "Loading mission projection…", status: "—", evidenceCount: "—", pendingReviews: "—", degraded: false,
  });
  useEffect(() => {
    let cancelled = false;
    async function refreshMissionRail() {
      try {
        const [missionRes, reviewRes] = await Promise.all([
          fetch("../../data/mission-ops.json", { cache: "no-store" }),
          fetch("../../data/mission-reviews.json", { cache: "no-store" }),
        ]);
        if (!missionRes.ok || !reviewRes.ok) throw new Error("projection unavailable");
        const mission = await missionRes.json();
        const reviews = await reviewRes.json();
        if (cancelled) return;
        setMissionRail({
          objective: mission.mission.objective,
          status: mission.mission.status.replaceAll("-", " "),
          evidenceCount: String((mission.evidence || []).filter((e) => e.classification === "verified-state").length),
          pendingReviews: String(reviews.pending_count || 0),
          degraded: false,
        });
      } catch {
        if (cancelled) return;
        setMissionRail({ objective: "Mission projection unavailable.", status: "degraded", evidenceCount: "—", pendingReviews: "—", degraded: true });
      }
    }
    refreshMissionRail();
    const id = setInterval(refreshMissionRail, 10000);
    return () => { cancelled = true; clearInterval(id); };
  }, []);

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

  // ---- Control tab: folded in from toys/fleetcore-control/app.js ----
  const [spawnForm, setSpawnForm] = useState({
    name: "", callsign: "", lat: "", lng: "", course: "0", speed: "0",
  });
  const [despawnId, setDespawnId] = useState("");
  const [timeScale, setTimeScale] = useState(1);
  const [harbor, setHarbor] = useState({
    phase: "idle", pilotId: null, pilotCallsign: null, harborPoint: null,
  });

  const flagshipPos = flagship ? flagship.position : null;

  const handleSpawnSubmit = (e) => {
    e.preventDefault();
    const lat = Number(spawnForm.lat);
    const lng = Number(spawnForm.lng);
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
      addLog("Spawn rejected — lat/lng must be numbers.");
      return;
    }
    const name = spawnForm.name.trim() || "Unnamed Contact";
    const callsign = spawnForm.callsign.trim() || name.toUpperCase();
    sendCommand({
      type: "spawn-passive-contact",
      id: `manual-${idSuffix()}`,
      name,
      callsign,
      position: { lat, lng },
      course: Number.isFinite(Number(spawnForm.course)) ? Number(spawnForm.course) : 0,
      speed_mps: Number.isFinite(Number(spawnForm.speed)) ? Number(spawnForm.speed) : 0,
    });
    addLog(`Spawned ${callsign} at ${lat.toFixed(3)}, ${lng.toFixed(3)}.`);
    setSpawnForm({ name: "", callsign: "", lat: "", lng: "", course: "0", speed: "0" });
  };

  const handleDespawn = (e) => {
    e.preventDefault();
    if (!despawnId) {
      addLog("Despawn rejected — no contact selected.");
      return;
    }
    const target = vessels.find((v) => v.id === despawnId);
    sendCommand({ type: "despawn-vessel", id: despawnId });
    addLog(`Despawn command sent for ${target ? target.callsign : despawnId}.`);
    setDespawnId("");
  };

  const handleResetFleet = () => {
    if (!window.confirm("Reset Monad and all three scout escorts to their starting position, course, speed, and route? This affects every connected visitor and cannot be undone.")) {
      return;
    }
    sendCommand({ type: "reset-fleet" });
    addLog("Fleet reset command sent.");
  };

  const handlePauseResume = () => {
    sendCommand({ type: snapshot?.clock_state === "running" ? "pause-clock" : "resume-clock" });
  };

  const handleApplyTimeScale = () => {
    const scale = Number(timeScale);
    if (!Number.isFinite(scale) || scale < 1) return;
    sendCommand({ type: "set-time-scale", scale: Math.round(scale) });
    addLog(`Time scale set to ${Math.round(scale)}x.`);
  };

  const runScenario = (kind) => {
    if (!flagshipPos) {
      addLog("Scenario rejected — no flagship position yet.");
      return;
    }
    const suffix = idSuffix();
    if (kind === "distress-call") {
      const callsign = `MAYDAY ${suffix.slice(-4).toUpperCase()}`;
      sendCommand({
        type: "spawn-passive-contact", id: `distress-${suffix}`, name: "Distressed Vessel", callsign,
        position: { lat: flagshipPos.lat + 0.06, lng: flagshipPos.lng + 0.04 }, course: 0, speed_mps: 0,
      });
      sendCommand({ type: "record-watch-event", message: `Distress call received from ${callsign}` });
      addLog(`Scenario: distress call from ${callsign}.`);
    } else if (kind === "storm-convoy") {
      [-0.12, 0, 0.12].forEach((offset, index) => {
        const id = `storm-${suffix}-${index}`;
        sendCommand({
          type: "spawn-passive-contact", id, name: `Storm Convoy ${index + 1}`, callsign: `CONVOY ${index + 1}`,
          position: { lat: flagshipPos.lat + 0.35, lng: flagshipPos.lng + offset }, course: 180, speed_mps: 7,
        });
        sendCommand({
          type: "set-route", vessel_id: id,
          route: [{ lat: flagshipPos.lat + 0.1, lng: flagshipPos.lng + offset * 0.4 }],
        });
      });
      sendCommand({ type: "record-watch-event", message: "Storm convoy of 3 vessels reported entering the area" });
      addLog("Scenario: storm convoy of 3 spawned.");
    } else if (kind === "collision-course") {
      const id = `collision-${suffix}`;
      const callsign = `BOGEY ${suffix.slice(-4).toUpperCase()}`;
      sendCommand({
        type: "spawn-passive-contact", id, name: "Unidentified Contact", callsign,
        position: { lat: flagshipPos.lat + 0.4, lng: flagshipPos.lng + 0.4 }, course: 225, speed_mps: 9,
      });
      sendCommand({ type: "set-route", vessel_id: id, route: [flagshipPos] });
      sendCommand({ type: "record-watch-event", message: "Contact on possible collision bearing with flagship" });
      addLog(`Scenario: ${callsign} on collision bearing.`);
    }
  };

  // Harbor Pilot Boarding — same multi-phase scenario as
  // fleetcore-control/app.js (see that file's comment for the full
  // rationale: manual phase advancement, no FleetCore-side state machine).
  const HARBOR_STEPS = {
    idle: {
      label: "Begin Harbor Approach",
      note: "Spawns the pilot boat and harbor traffic at a synthetic harbor point; pilot boat gets a real intercept route toward the flagship.",
      run: () => {
        if (!flagshipPos) return addLog("Harbor scenario rejected — no flagship position yet.");
        const suffix = idSuffix();
        const harborPoint = { lat: flagshipPos.lat + 0.5, lng: flagshipPos.lng - 0.35 };
        const pilotId = `harbor-pilot-${suffix}`;
        const pilotCallsign = `PILOT BOAT ${suffix.slice(-3).toUpperCase()}`;
        sendCommand({
          type: "spawn-passive-contact", id: pilotId, name: "Harbor Pilot Boat", callsign: pilotCallsign,
          position: harborPoint, course: 0, speed_mps: 6,
        });
        sendCommand({ type: "set-route", vessel_id: pilotId, route: [flagshipPos] });
        [0, 1].forEach((index) => {
          sendCommand({
            type: "spawn-passive-contact", id: `harbor-traffic-${suffix}-${index}`, name: `Harbor Traffic ${index + 1}`,
            callsign: `HARBOR TRAFFIC ${index + 1}`,
            position: {
              lat: harborPoint.lat + (index === 0 ? 0.02 : -0.03),
              lng: harborPoint.lng + (index === 0 ? -0.02 : 0.015),
            },
            course: 90 + index * 40, speed_mps: 3,
          });
        });
        sendCommand({
          type: "record-watch-event",
          message: `Harbor Pilot requested. ${pilotCallsign} departing harbor — ETA approximately 12 minutes.`,
        });
        setHarbor({ phase: "inbound", pilotId, pilotCallsign, harborPoint });
      },
    },
    inbound: {
      label: "Confirm Pilot Boat Detected",
      note: "Fleet Motion and Periscope should already show the pilot boat closing — this advances the watch narrative, it doesn't move anything itself.",
      run: () => {
        sendCommand({ type: "record-watch-event", message: `${harbor.pilotCallsign} visually acquired, closing on intercept course.` });
        setHarbor((h) => ({ ...h, phase: "detected" }));
      },
    },
    detected: {
      label: "Acknowledge Pilot Boat",
      note: "Grant permission to come alongside — this is the radio trigger the scenario waits on.",
      hail: () => `"Monad, this is ${harbor.pilotCallsign}. Request permission to come alongside."`,
      run: () => {
        sendCommand({ type: "record-watch-event", message: `Monad to ${harbor.pilotCallsign}: Permission granted, come alongside.` });
        if (flagshipPos) sendCommand({ type: "set-route", vessel_id: harbor.pilotId, route: [flagshipPos] });
        setHarbor((h) => ({ ...h, phase: "hailed" }));
      },
    },
    hailed: {
      label: "Confirm Boarding",
      note: "Pilot boat should now be closing tightly on the flagship for the boarding transfer.",
      run: () => {
        sendCommand({ type: "record-watch-event", message: "Harbor Pilot aboard." });
        setHarbor((h) => ({ ...h, phase: "boarding" }));
      },
    },
    boarding: {
      label: "Grant the Conn",
      note: "Transfers temporary ship-handling authority and issues the pilot's staged helm orders as a real route on the flagship itself.",
      hail: () => `"Captain, request the conn."`,
      run: () => {
        if (!flagship) return addLog("No flagship position yet.");
        sendCommand({ type: "record-watch-event", message: "Captain to Harbor Pilot: The conn is yours." });
        const berth = harbor.harborPoint;
        const start = flagship.position;
        const legs = [
          { lat: start.lat + (berth.lat - start.lat) * 0.33, lng: start.lng + (berth.lng - start.lng) * 0.2, order: "Port five" },
          { lat: start.lat + (berth.lat - start.lat) * 0.6, lng: start.lng + (berth.lng - start.lng) * 0.55, order: "Dead slow ahead" },
          { lat: start.lat + (berth.lat - start.lat) * 0.85, lng: start.lng + (berth.lng - start.lng) * 0.8, order: "Midships" },
          { lat: berth.lat, lng: berth.lng, order: "Ease to starboard" },
        ];
        sendCommand({ type: "set-route", vessel_id: flagship.id, route: legs.map(({ lat, lng }) => ({ lat, lng })) });
        legs.forEach((leg) => sendCommand({ type: "record-watch-event", message: `Pilot orders: ${leg.order}` }));
        setHarbor((h) => ({ ...h, phase: "transit" }));
      },
    },
    transit: {
      label: "Arrive at Berth",
      note: "Flagship should be following the staged route toward the harbor point. Pilot boat departs once berthed.",
      run: () => {
        sendCommand({ type: "record-watch-event", message: "Monad arrives at berth. Harbor transit complete." });
        if (harbor.pilotId && harbor.harborPoint) {
          sendCommand({ type: "set-route", vessel_id: harbor.pilotId, route: [harbor.harborPoint] });
        }
        sendCommand({
          type: "record-watch-event",
          message: `${harbor.pilotCallsign} disembarks and returns to harbor. Harbor Pilot Boarding scenario complete.`,
        });
        setHarbor((h) => ({ ...h, phase: "complete" }));
      },
    },
  };
  const HARBOR_PHASE_LABELS = {
    idle: "Not started", inbound: "Phase 1 — Inbound Transit", detected: "Phase 2 — Detection",
    hailed: "Phase 3 — Radio Contact", boarding: "Phase 4 — Boarding",
    transit: "Phase 5–6 — Conn Transferred / Harbor Transit", complete: "Phase 7 — Completion",
  };
  const currentHarborStep = HARBOR_STEPS[harbor.phase];

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
      <a href="../../index.html" className="bs-mono monad-home-link">⚓ Fleet Monad</a>
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
        .station-tab-btn {
          display: flex; align-items: center; gap: 6px;
          background: transparent; border: none; border-bottom: 2px solid transparent;
          color: #6B7C93; font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase;
          padding: 9px 14px; cursor: pointer; transition: color 120ms ease, border-color 120ms ease;
        }
        .station-tab-btn:hover { color: #DCE6F2; }
        .station-tab-btn.is-active { color: #E8A33D; border-bottom-color: #E8A33D; }
        .monad-home-link {
          position: fixed; top: 10px; left: 10px; z-index: 9999; font-size: 11px;
          letter-spacing: 0.05em; color: #9BB0C8; background: rgba(11,18,32,0.85);
          border: 1px solid rgba(79,209,197,0.35); border-radius: 4px; padding: 5px 10px;
          text-decoration: none; transition: color 150ms ease, border-color 150ms ease;
        }
        .monad-home-link:hover { color: #4FD1C5; border-color: #4FD1C5; }
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

      {/* Station tabs */}
      <nav className="bs-mono" style={styles.stationTabs} aria-label="Bridge stations">
        {[
          { id: "bridge", label: "Bridge", icon: Anchor },
          { id: "control", label: "Control", icon: SlidersHorizontal },
          { id: "radio", label: "Radio", icon: Radio },
          { id: "raw", label: "Raw Feed", icon: Terminal },
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            className={`bs-mono station-tab-btn ${activeTab === id ? "is-active" : ""}`}
            style={styles.stationTabBtn}
            onClick={() => setActiveTab(id)}
          >
            <Icon size={12} />
            {label}
          </button>
        ))}
      </nav>

      {/* Mission Record rail — persistent across every tab */}
      <div className="bs-mono" style={styles.missionRail}>
        <span style={styles.missionRailLabel}>MISSION</span>
        <span style={{ ...styles.missionRailObjective, color: missionRail.degraded ? "#6B7C93" : "#DCE6F2" }}>
          {missionRail.objective}
        </span>
        <span style={{ ...styles.missionRailBadge, color: missionRail.degraded ? "#E05252" : "#4FD1C5", borderColor: missionRail.degraded ? "#E0525244" : "#4FD1C544" }}>
          {missionRail.status}
        </span>
        <span style={styles.missionRailStat}>EVIDENCE {missionRail.evidenceCount}</span>
        <span style={styles.missionRailStat}>REVIEWS {missionRail.pendingReviews}</span>
        <a href="../agent-ops/" style={styles.missionRailLink}>Agent Ops →</a>
      </div>

      {/* Main dual view */}
      <div className="bs-main" style={{ ...styles.main, display: activeTab === "bridge" ? "grid" : "none" }}>
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
      <div style={{ ...styles.actionRow, display: activeTab === "bridge" ? "block" : "none" }}>
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

      {/* CONTROL tab — folded in from toys/fleetcore-control/ */}
      {activeTab === "control" && (
        <div className="bs-mono" style={styles.controlPane}>
          {!commandAuthority && (
            <p style={styles.controlWarn}>
              This connection has not been granted command authority yet — commands below may be rejected.
            </p>
          )}
          <p style={styles.controlNote}>
            This world is shared by every visitor. Every command below acts on the live world for everyone connected, not just you.
          </p>

          <div style={styles.controlGrid}>
            <section style={styles.controlCard}>
              <h3 className="bs-display" style={styles.controlCardTitle}>Clock</h3>
              <div style={styles.controlRow}>
                <button className="cmd-btn" onClick={handlePauseResume}>
                  {snapshot?.clock_state === "running" ? "Pause" : "Resume"}
                </button>
                <input
                  type="number" min="1" max="500" value={timeScale}
                  onChange={(e) => setTimeScale(e.target.value)}
                  style={styles.controlInput}
                />
                <button className="cmd-btn" onClick={handleApplyTimeScale}>Apply Scale</button>
              </div>
              <div style={styles.controlRow}>
                <button className="cmd-btn" style={styles.dangerBtn} onClick={handleResetFleet}>Reset Fleet</button>
              </div>
            </section>

            <section style={styles.controlCard}>
              <h3 className="bs-display" style={styles.controlCardTitle}>Spawn Passive Contact</h3>
              <form onSubmit={handleSpawnSubmit} style={styles.controlForm}>
                <input placeholder="Name" value={spawnForm.name} style={styles.controlInput}
                  onChange={(e) => setSpawnForm((f) => ({ ...f, name: e.target.value }))} />
                <input placeholder="Callsign" value={spawnForm.callsign} style={styles.controlInput}
                  onChange={(e) => setSpawnForm((f) => ({ ...f, callsign: e.target.value }))} />
                <div style={styles.controlRow}>
                  <input placeholder="Lat" value={spawnForm.lat} style={styles.controlInput}
                    onChange={(e) => setSpawnForm((f) => ({ ...f, lat: e.target.value }))} />
                  <input placeholder="Lng" value={spawnForm.lng} style={styles.controlInput}
                    onChange={(e) => setSpawnForm((f) => ({ ...f, lng: e.target.value }))} />
                </div>
                <div style={styles.controlRow}>
                  <input placeholder="Course°" value={spawnForm.course} style={styles.controlInput}
                    onChange={(e) => setSpawnForm((f) => ({ ...f, course: e.target.value }))} />
                  <input placeholder="Speed m/s" value={spawnForm.speed} style={styles.controlInput}
                    onChange={(e) => setSpawnForm((f) => ({ ...f, speed: e.target.value }))} />
                </div>
                <button className="cmd-btn" type="submit">Spawn</button>
              </form>
            </section>

            <section style={styles.controlCard}>
              <h3 className="bs-display" style={styles.controlCardTitle}>Despawn Contact</h3>
              <form onSubmit={handleDespawn} style={styles.controlForm}>
                <select value={despawnId} onChange={(e) => setDespawnId(e.target.value)} style={styles.controlInput}>
                  <option value="">Select a contact…</option>
                  {vessels.filter((v) => v.kind !== "flagship").map((v) => (
                    <option key={v.id} value={v.id}>{v.callsign}</option>
                  ))}
                </select>
                <button className="cmd-btn" style={styles.dangerBtn} type="submit">Despawn</button>
              </form>
            </section>

            <section style={styles.controlCard}>
              <h3 className="bs-display" style={styles.controlCardTitle}>Quick Scenarios</h3>
              <div style={styles.controlForm}>
                <button className="cmd-btn" onClick={() => runScenario("distress-call")}>Distress Call</button>
                <button className="cmd-btn" onClick={() => runScenario("storm-convoy")}>Storm Convoy</button>
                <button className="cmd-btn" onClick={() => runScenario("collision-course")}>Collision Course</button>
              </div>
            </section>

            <section style={{ ...styles.controlCard, gridColumn: "1 / -1" }}>
              <h3 className="bs-display" style={styles.controlCardTitle}>Harbor Pilot Boarding</h3>
              <p style={styles.controlNote}>{HARBOR_PHASE_LABELS[harbor.phase]}</p>
              {currentHarborStep && (
                <>
                  {currentHarborStep.hail && (
                    <p style={styles.harborHail}>{currentHarborStep.hail()}</p>
                  )}
                  <p style={styles.controlNote}>{currentHarborStep.note}</p>
                  <div style={styles.controlRow}>
                    <button className="cmd-btn" onClick={currentHarborStep.run}>{currentHarborStep.label}</button>
                    {harbor.phase !== "idle" && (
                      <button
                        className="cmd-btn"
                        style={styles.dangerBtn}
                        onClick={() => {
                          setHarbor({ phase: "idle", pilotId: null, pilotCallsign: null, harborPoint: null });
                          addLog("Harbor scenario tracker reset. Previously spawned vessels are still in the world — there is no despawn-all command.");
                        }}
                      >
                        Reset Tracker
                      </button>
                    )}
                  </div>
                </>
              )}
            </section>
          </div>
        </div>
      )}

      {/* RADIO tab — folded in from toys/radio-console/, same iframe embed old Bridge used */}
      {activeTab === "radio" && (
        <div style={styles.radioPane}>
          <iframe
            title="Radio Console instrument"
            src="../radio-console/"
            style={styles.radioFrame}
          />
        </div>
      )}

      {/* RAW FEED tab — folded in from toys/fleetcore-live/, table form instead of the Leaflet map */}
      {activeTab === "raw" && (
        <div className="bs-mono" style={styles.rawPane}>
          <div style={styles.rawStrip}>
            <span>TICK <b style={{ color: "#4FD1C5" }}>{snapshot?.tick ?? "—"}</b></span>
            <span>SIM TIME <b style={{ color: "#4FD1C5" }}>{snapshot?.sim_time || "—"}</b></span>
            <span>CLOCK <b style={{ color: "#4FD1C5" }}>{snapshot?.clock_state || "—"}</b></span>
            <span>TIME SCALE <b style={{ color: "#4FD1C5" }}>{snapshot?.time_scale ?? "—"}x</b></span>
            <span>AUTHORITY <b style={{ color: commandAuthority ? "#4FD1C5" : "#E05252" }}>{commandAuthority ? "Command" : "Read-only"}</b></span>
            <span>EVENT RETENTION <b style={{ color: "#4FD1C5" }}>{snapshot?.vessel_event_retention ?? "—"}</b></span>
          </div>

          <h3 className="bs-display" style={styles.rawHeading}>Vessels ({vessels.length})</h3>
          <div style={styles.rawTableWrap}>
            <table style={styles.rawTable}>
              <thead>
                <tr>
                  <th style={styles.rawTh}>Callsign</th>
                  <th style={styles.rawTh}>Kind</th>
                  <th style={styles.rawTh}>Status</th>
                  <th style={styles.rawTh}>Position</th>
                  <th style={styles.rawTh}>Course</th>
                  <th style={styles.rawTh}>Speed</th>
                  <th style={styles.rawTh}>Route legs</th>
                </tr>
              </thead>
              <tbody>
                {vessels.map((v) => (
                  <tr key={v.id}>
                    <td style={styles.rawTd}>{v.callsign}</td>
                    <td style={styles.rawTd}>{v.kind}</td>
                    <td style={styles.rawTd}>{v.status}</td>
                    <td style={styles.rawTd}>{v.position.lat.toFixed(4)}, {v.position.lng.toFixed(4)}</td>
                    <td style={styles.rawTd}>{Math.round(v.course)}°</td>
                    <td style={styles.rawTd}>{v.speed_mps.toFixed(1)} m/s</td>
                    <td style={styles.rawTd}>{v.route ? v.route.length : 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h3 className="bs-display" style={styles.rawHeading}>Watch Events ({(snapshot?.watch_events || []).length})</h3>
          <ul style={styles.rawList}>
            {(snapshot?.watch_events || []).slice(-10).reverse().map((event, i) => (
              <li key={i} style={styles.rawListItem}>[tick {event.tick}] {event.message}</li>
            ))}
          </ul>

          <h3 className="bs-display" style={styles.rawHeading}>Vessel Events ({(snapshot?.vessel_events || []).length})</h3>
          <ul style={styles.rawList}>
            {(snapshot?.vessel_events || []).slice(-10).reverse().map((event, i) => (
              <li key={i} style={styles.rawListItem}>[tick {event.tick}] {event.vessel_id}: {event.type}</li>
            ))}
          </ul>
        </div>
      )}

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

  stationTabs: {
    display: "flex", gap: 2, background: "#0D1626", borderBottom: "1px solid #1E2C42", padding: "0 14px",
  },
  stationTabBtn: {},

  missionRail: {
    display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap",
    padding: "7px 14px", background: "#0D1626", borderBottom: "1px solid #1E2C42", fontSize: 11,
  },
  missionRailLabel: { color: "#6B7C93", letterSpacing: "0.1em", flexShrink: 0 },
  missionRailObjective: { flex: "1 1 auto", minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" },
  missionRailBadge: { padding: "1px 7px", borderRadius: 3, border: "1px solid #4FD1C544", flexShrink: 0, textTransform: "uppercase" },
  missionRailStat: { color: "#6B7C93", flexShrink: 0 },
  missionRailLink: { color: "#4FD1C5", textDecoration: "none", flexShrink: 0 },

  controlPane: { padding: "16px", overflowY: "auto", flex: "1 1 auto", minHeight: 320 },
  controlWarn: { color: "#E8A33D", fontSize: 11, marginBottom: 10 },
  controlNote: { color: "#6B7C93", fontSize: 11, marginBottom: 12, lineHeight: 1.5 },
  controlGrid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 },
  controlCard: {
    background: "#111A2B", border: "1px solid #1E2C42", borderRadius: 6, padding: "14px 16px",
  },
  controlCardTitle: { fontSize: 12, letterSpacing: "0.1em", color: "#DCE6F2", marginBottom: 10, textTransform: "uppercase" },
  controlRow: { display: "flex", gap: 8, marginBottom: 8, flexWrap: "wrap" },
  controlForm: { display: "flex", flexDirection: "column", gap: 8 },
  controlInput: {
    background: "#0D1626", border: "1px solid #1E2C42", borderRadius: 3, color: "#DCE6F2",
    padding: "8px 10px", fontSize: 12, fontFamily: "'JetBrains Mono', monospace", flex: "1 1 0",
  },
  dangerBtn: { background: "#E05252" },
  harborHail: {
    color: "#4FD1C5", fontStyle: "italic", fontSize: 12, marginBottom: 8,
    borderLeft: "2px solid #4FD1C5", paddingLeft: 10,
  },

  radioPane: { flex: "1 1 auto", minHeight: 420, display: "flex" },
  radioFrame: { flex: "1 1 auto", width: "100%", border: "none" },

  rawPane: { padding: "16px", overflowY: "auto", flex: "1 1 auto", minHeight: 320, fontSize: 12 },
  rawStrip: {
    display: "flex", flexWrap: "wrap", gap: 16, color: "#6B7C93", fontSize: 11,
    paddingBottom: 12, marginBottom: 14, borderBottom: "1px solid #1E2C42",
  },
  rawHeading: { fontSize: 12, letterSpacing: "0.08em", color: "#DCE6F2", textTransform: "uppercase", margin: "16px 0 8px" },
  rawTableWrap: { overflowX: "auto" },
  rawTable: { width: "100%", borderCollapse: "collapse", fontSize: 11 },
  rawTh: { textAlign: "left", color: "#6B7C93", padding: "6px 10px", borderBottom: "1px solid #1E2C42" },
  rawTd: { padding: "6px 10px", borderBottom: "1px solid #14203380", color: "#DCE6F2" },
  rawList: { listStyle: "none", padding: 0, margin: 0 },
  rawListItem: { padding: "5px 0", borderBottom: "1px solid #14203380", color: "#9BB0C8", fontSize: 11 },
};
