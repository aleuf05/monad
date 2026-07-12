(function () {
  "use strict";

  const STORAGE_KEY = "monad.fleetMotion.state";
  const SCHEMA_VERSION = 2;
  const KMH_TO_KNOTS = 0.539956803;
  const KM_TO_NAUTICAL_MILES = 0.539956803;
  const CONTACT_COLORS = ["#8ad7c1", "#d8b46a", "#94bfe8", "#d9ecf0", "#9ee6f0", "#e8c989"];

  function normalizeDegrees(value) {
    return ((Number(value || 0) % 360) + 360) % 360;
  }

  function clonePoint(point) {
    if (!point || typeof point.lat !== "number" || typeof point.lng !== "number") return null;
    return { lat: Number(point.lat), lng: Number(point.lng) };
  }

  function distanceKm(start, end) {
    const earthRadiusKm = 6371;
    const latDelta = (end.lat - start.lat) * Math.PI / 180;
    const lngDelta = (end.lng - start.lng) * Math.PI / 180;
    const startLat = start.lat * Math.PI / 180;
    const endLat = end.lat * Math.PI / 180;
    const haversine =
      Math.sin(latDelta / 2) ** 2 +
      Math.cos(startLat) * Math.cos(endLat) * Math.sin(lngDelta / 2) ** 2;
    return earthRadiusKm * 2 * Math.atan2(Math.sqrt(haversine), Math.sqrt(1 - haversine));
  }

  function bearingDegrees(start, end) {
    const startLat = start.lat * Math.PI / 180;
    const endLat = end.lat * Math.PI / 180;
    const lngDelta = (end.lng - start.lng) * Math.PI / 180;
    const y = Math.sin(lngDelta) * Math.cos(endLat);
    const x =
      Math.cos(startLat) * Math.sin(endLat) -
      Math.sin(startLat) * Math.cos(endLat) * Math.cos(lngDelta);
    return normalizeDegrees(Math.atan2(y, x) * 180 / Math.PI);
  }

  function normalizeFleetMotionState(candidate) {
    if (!candidate || candidate.schemaVersion !== SCHEMA_VERSION) return null;
    // Every nested object spreads the candidate first, then overrides only the
    // fields this contract cares about — producers (Fleet Motion) can carry
    // extra fields (designSettings, waypointMode, ...) through a write/read
    // round trip without this contract silently dropping them.
    return {
      ...candidate,
      schemaVersion: SCHEMA_VERSION,
      savedAt: candidate.savedAt || null,
      dataSource: candidate.dataSource || "local-simulation",
      // Only meaningful when dataSource is "fleetcore-live" -- Fleet Motion
      // is the only writer today and it's always false outside live mode,
      // but default explicitly rather than lean on that as a promise.
      liveCommandAuthority: Boolean(candidate.liveCommandAuthority),
      activePresetId: candidate.activePresetId || "freeplay",
      flagship: {
        ...(candidate.flagship || {}),
        position: clonePoint(candidate.flagship?.position)
      },
      navigation: {
        ...(candidate.navigation || {}),
        destination: clonePoint(candidate.navigation?.destination),
        finalDestination: clonePoint(candidate.navigation?.finalDestination),
        waypoints: (candidate.navigation?.waypoints || []).map(clonePoint).filter(Boolean),
        routeQueue: (candidate.navigation?.routeQueue || []).map(clonePoint).filter(Boolean),
        lastStatus: candidate.navigation?.lastStatus || "Holding",
        lastNavigationMessage: candidate.navigation?.lastNavigationMessage || "Clear"
      },
      time: {
        ...(candidate.time || {}),
        timeWarp: Number(candidate.time?.timeWarp ?? 1),
        lastMovingWarp: Number(candidate.time?.lastMovingWarp ?? 1),
        simulationClockSeconds: Number(candidate.time?.simulationClockSeconds ?? 0)
      },
      escorts: {
        ...(candidate.escorts || {}),
        modeId: candidate.escorts?.modeId || "loose",
        ships: (candidate.escorts?.ships || []).map((ship) => ({
          ...ship,
          position: clonePoint(ship.position),
          speedKmh: Number(ship.speedKmh || 0),
          headingDegrees: ship.headingDegrees === null || ship.headingDegrees === undefined
            ? null
            : normalizeDegrees(ship.headingDegrees)
        })).filter((ship) => ship.position)
      },
      contacts: {
        ...(candidate.contacts || {}),
        mode: candidate.contacts?.mode || "passive",
        ships: (candidate.contacts?.ships || []).map((ship) => ({
          ...ship,
          position: clonePoint(ship.position),
          speedKmh: Number(ship.speedKmh || 0),
          headingDegrees: ship.headingDegrees === null || ship.headingDegrees === undefined
            ? null
            : normalizeDegrees(ship.headingDegrees),
          status: ship.status || "Transiting"
        })).filter((ship) => ship.position)
      },
      selection: {
        ...(candidate.selection || {}),
        selectedShipId: candidate.selection?.selectedShipId ?? null
      }
    };
  }

  function readFleetMotionState() {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      return raw ? normalizeFleetMotionState(JSON.parse(raw)) : null;
    } catch (error) {
      return null;
    }
  }

  function writeFleetMotionState(state) {
    const normalized = normalizeFleetMotionState(state);
    if (!normalized) return false;
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(normalized));
    return true;
  }

  function toTitle(value) {
    return String(value || "")
      .toLowerCase()
      .replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  function contactFromVessel(vessel, origin, index, source, selectedId) {
    const position = clonePoint(vessel.position);
    if (!position || !origin) return null;
    const callsign = vessel.callsign || vessel.name || vessel.id;
    const role = vessel.role || vessel.kind || "vessel";
    return {
      id: vessel.id,
      name: toTitle(vessel.name || callsign),
      callsign: String(callsign).toUpperCase(),
      class: role,
      mission: role === "passive-traffic" || source === "fleet-motion-passive-contact"
        ? "Local Traffic"
        : "Fleet Screen",
      status: vessel.status || (vessel.blocked ? "Holding" : "Nominal"),
      report: `${String(callsign).toUpperCase()} observed from shared fleet state.`,
      color: CONTACT_COLORS[index % CONTACT_COLORS.length],
      latitude: position.lat,
      longitude: position.lng,
      bearing: bearingDegrees(origin, position),
      range: Math.max(0.1, distanceKm(origin, position) * KM_TO_NAUTICAL_MILES),
      course: vessel.headingDegrees === null || vessel.headingDegrees === undefined
        ? null
        : normalizeDegrees(vessel.headingDegrees),
      speed: Number(vessel.speedKmh || 0) * KMH_TO_KNOTS,
      lastUpdate: new Date().toISOString(),
      confidence: 1,
      source,
      selected: selectedId != null && String(vessel.id) === String(selectedId)
    };
  }

  function toScoutContacts(state) {
    const normalized = normalizeFleetMotionState(state);
    const origin = normalized?.flagship?.position;
    if (!normalized || !origin) return [];
    const selectedId = normalized.selection?.selectedShipId ?? null;
    const escorts = normalized.escorts.ships.map((ship, index) =>
      contactFromVessel(
        {
          ...ship,
          callsign: ship.name?.replace("ESCORT", "SCOUT") || ship.id,
          kind: "scout"
        },
        origin,
        index,
        "fleet-motion-escort",
        selectedId
      )
    );
    const passive = normalized.contacts.ships.map((ship, index) =>
      contactFromVessel(
        {
          ...ship,
          kind: "passive-traffic",
          callsign: ship.name || ship.id
        },
        origin,
        escorts.length + index,
        "fleet-motion-passive-contact",
        selectedId
      )
    );
    return [...escorts, ...passive].filter(Boolean);
  }

  function fromFleetCoreSnapshot(snapshot) {
    if (!snapshot || !Array.isArray(snapshot.vessels)) return null;
    const flagship = snapshot.vessels.find((vessel) => vessel.kind === "flagship");
    const scouts = snapshot.vessels.filter((vessel) => vessel.kind === "scout");
    const passive = snapshot.vessels.filter((vessel) => vessel.kind === "passive-traffic");
    return normalizeFleetMotionState({
      schemaVersion: SCHEMA_VERSION,
      savedAt: snapshot.sim_time || null,
      dataSource: "fleetcore-live",
      activePresetId: "fleetcore",
      flagship: {
        position: clonePoint(flagship?.position),
        headingDegrees: flagship?.course ?? null,
        speedKmh: Number(flagship?.speed_mps || 0) * 3.6
      },
      navigation: {
        routeQueue: flagship?.route || [],
        waypoints: [],
        lastStatus: flagship?.status || "Holding",
        lastNavigationMessage: "FleetCore snapshot"
      },
      time: {
        timeWarp: snapshot.time_scale || 1,
        lastMovingWarp: snapshot.time_scale || 1,
        simulationClockSeconds: snapshot.tick || 0
      },
      escorts: {
        modeId: "shared",
        ships: scouts.map((vessel) => ({
          id: vessel.id,
          name: vessel.callsign || vessel.name,
          position: vessel.position,
          speedKmh: Number(vessel.speed_mps || 0) * 3.6,
          headingDegrees: vessel.course
        }))
      },
      contacts: {
        mode: "passive",
        ships: passive.map((vessel) => ({
          id: vessel.id,
          name: vessel.callsign || vessel.name,
          role: "passive traffic",
          position: vessel.position,
          speedKmh: Number(vessel.speed_mps || 0) * 3.6,
          headingDegrees: vessel.course,
          status: vessel.status
        }))
      }
    });
  }

  window.MonadFleetState = {
    storageKey: STORAGE_KEY,
    schemaVersion: SCHEMA_VERSION,
    read: readFleetMotionState,
    write: writeFleetMotionState,
    normalize: normalizeFleetMotionState,
    toScoutContacts,
    fromFleetCoreSnapshot,
    utils: {
      bearingDegrees,
      distanceKm,
      normalizeDegrees
    }
  };
})();
