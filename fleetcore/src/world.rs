use crate::clock::{ClockState, WorldClock};
use crate::command::Command;
use crate::event::Event;
use crate::geography;
use crate::route::{bearing_degrees, distance_meters, point_at_distance};
use crate::vessel::{
    normalize_degrees, quantize, EscortMode, Position, Vessel, VesselEvent, VesselKind,
    VesselStatus,
};
use serde::{Deserialize, Serialize};

const ARRIVAL_RADIUS_METERS: f64 = 80.0;

// Escort formation geometry: scouts are spread evenly across this many
// degrees, centered dead astern (180 deg relative to the flagship's
// course), sorted by vessel id for a stable slot assignment. Radius varies
// by mode; Patrol reuses Loose's radius and adds a slow, deterministic
// bearing sweep on top of each slot's base offset, driven by tick count
// (not wall-clock time) so it stays replay-deterministic like everything
// else in this engine.
const ESCORT_WEDGE_SPREAD_DEGREES: f64 = 70.0;
const ESCORT_LOOSE_RADIUS_METERS: f64 = 1200.0;
const ESCORT_TIGHT_RADIUS_METERS: f64 = 350.0;
const ESCORT_PATROL_SWEEP_DEGREES: f64 = 40.0;
const ESCORT_PATROL_SWEEP_RATE: f64 = 0.002;

fn escort_station(
    leader: &Vessel,
    slot_index: usize,
    slot_count: usize,
    mode: EscortMode,
    tick: u64,
) -> Position {
    let slot_offset = if slot_count <= 1 {
        0.0
    } else {
        -ESCORT_WEDGE_SPREAD_DEGREES / 2.0
            + ESCORT_WEDGE_SPREAD_DEGREES * (slot_index as f64) / ((slot_count - 1) as f64)
    };
    let sweep = if mode == EscortMode::Patrol {
        ESCORT_PATROL_SWEEP_DEGREES * ((tick as f64) * ESCORT_PATROL_SWEEP_RATE).sin()
    } else {
        0.0
    };
    let radius = match mode {
        EscortMode::Tight => ESCORT_TIGHT_RADIUS_METERS,
        _ => ESCORT_LOOSE_RADIUS_METERS,
    };
    let bearing = normalize_degrees(leader.course + 180.0 + slot_offset + sweep);
    point_at_distance(leader.position, bearing, radius)
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct WatchEvent {
    pub tick: u64,
    pub sim_time: String,
    pub message: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct World {
    pub schema_version: String,
    pub world_id: String,
    pub clock: WorldClock,
    pub vessels: Vec<Vessel>,
    pub event_sequence: u64,
    pub watch_events: Vec<WatchEvent>,
    // Defaulted so seed/state files saved before this field existed still
    // load fine -- absent means Off, the pre-existing behavior.
    #[serde(default)]
    pub escort_mode: EscortMode,
    // Structured per-vessel route/motion events -- see VesselEvent's own
    // doc comment. Grows forever, same as watch_events, never truncated
    // server-side; clients diff against length/tick to find what's new
    // (same pattern renderWatchEvents already uses client-side). Defaulted
    // for backward compat with state files saved before this existed.
    #[serde(default)]
    pub vessel_events: Vec<VesselEvent>,
}

impl World {
    pub fn normalize(&mut self) {
        for vessel in &mut self.vessels {
            vessel.normalize();
        }
        self.vessels.sort_by(|a, b| a.id.cmp(&b.id));
    }

    pub fn apply_command(&mut self, command: Command) -> Result<Event, String> {
        let event_type = match &command {
            Command::SetRoute { vessel_id, route } => {
                // find_map (not find + a second zone_containing call) so
                // there's no separate .expect() that would panic -- and
                // therefore poison the Mutex<World> for every future
                // command -- if is_on_land and zone_containing ever
                // disagreed after a future refactor of either.
                if let Some((waypoint, zone)) = route
                    .iter()
                    .find_map(|point| geography::zone_containing(point).map(|zone| (point, zone)))
                {
                    return Err(format!(
                        "route rejected: waypoint ({}, {}) is on land ({})",
                        waypoint.lat, waypoint.lng, zone.name
                    ));
                }
                let tick = self.clock.tick;
                let sim_time = self.clock.sim_time();

                // Route replacement as a first-class event: a vessel that
                // was genuinely underway on a real route and gets a new one
                // holds its current position (no snap/jump), keeps moving
                // (status stays Underway), and gets its heading recomputed
                // toward the new first waypoint immediately -- it never
                // passes through Arrived/Holding on the way, which is what
                // previously let a same-tick replacement get misread
                // downstream as "arrived, then a new route was assigned"
                // instead of what actually happened, one continuous order.
                // A vessel that was NOT underway on a real route (Holding,
                // Arrived, Paused, or a scout with no route) gets a fresh
                // assignment instead -- there is nothing to replace.
                let event_to_emit: Option<VesselEvent> = {
                    let vessel = self
                        .vessel_mut(vessel_id)
                        .ok_or_else(|| format!("unknown vessel '{vessel_id}'"))?;
                    if route.is_empty() {
                        vessel.route = vec![];
                        vessel.status = VesselStatus::Holding;
                        vessel.last_update = sim_time.clone();
                        Some(VesselEvent::Holding {
                            vessel_id: vessel_id.clone(),
                            tick,
                            sim_time: sim_time.clone(),
                        })
                    } else if vessel.status == VesselStatus::Underway && !vessel.route.is_empty() {
                        let old_route_id = vessel.route_id;
                        let old_active_waypoint = vessel.route[0];
                        vessel.route_id += 1;
                        vessel.route = route.clone();
                        vessel.course = quantize(bearing_degrees(vessel.position, route[0]));
                        vessel.status = VesselStatus::Underway;
                        vessel.last_update = sim_time.clone();
                        Some(VesselEvent::RouteReplaced {
                            vessel_id: vessel_id.clone(),
                            old_route_id,
                            old_active_waypoint,
                            new_route_id: vessel.route_id,
                            new_first_waypoint: route[0],
                            remaining_leg_count: route.len(),
                            issuing_authority: "operator".to_string(),
                            tick,
                            sim_time: sim_time.clone(),
                        })
                    } else {
                        vessel.route_id += 1;
                        vessel.route = route.clone();
                        vessel.status = VesselStatus::Underway;
                        vessel.last_update = sim_time.clone();
                        None
                    }
                };
                if let Some(event) = event_to_emit {
                    self.vessel_events.push(event);
                }
                "route-set"
            }
            Command::PauseClock => {
                self.clock.state = ClockState::Paused;
                for vessel in &mut self.vessels {
                    if vessel.status == VesselStatus::Underway
                        || vessel.status == VesselStatus::Transiting
                    {
                        vessel.status = VesselStatus::Paused;
                        vessel.last_update = self.clock.sim_time();
                    }
                }
                "clock-paused"
            }
            Command::ResumeClock => {
                self.clock.state = ClockState::Running;
                let sim_time = self.clock.sim_time();
                for vessel in &mut self.vessels {
                    if vessel.status == VesselStatus::Paused {
                        vessel.status = if vessel.route.is_empty() {
                            VesselStatus::Transiting
                        } else {
                            VesselStatus::Underway
                        };
                        vessel.last_update = sim_time.clone();
                    }
                }
                "clock-resumed"
            }
            Command::SetTimeScale { scale } => {
                self.clock.time_scale = (*scale).clamp(1, 500);
                "time-scale-set"
            }
            Command::SpawnPassiveContact {
                id,
                name,
                callsign,
                position,
                course,
                speed_mps,
            } => {
                if self.vessels.iter().any(|vessel| vessel.id == *id) {
                    return Err(format!("vessel '{id}' already exists"));
                }
                if let Some(zone) = geography::zone_containing(position) {
                    return Err(format!(
                        "spawn rejected: position ({}, {}) is on land ({})",
                        position.lat, position.lng, zone.name
                    ));
                }
                let mut vessel = Vessel {
                    id: id.clone(),
                    name: name.clone(),
                    callsign: callsign.clone(),
                    kind: VesselKind::PassiveTraffic,
                    position: *position,
                    course: normalize_degrees(*course),
                    speed_mps: speed_mps.max(0.0),
                    status: VesselStatus::Transiting,
                    route: Vec::new(),
                    last_update: self.clock.sim_time(),
                    route_id: 0,
                };
                vessel.normalize();
                self.vessels.push(vessel);
                self.vessels.sort_by(|a, b| a.id.cmp(&b.id));
                "passive-contact-spawned"
            }
            Command::DespawnVessel { id } => {
                let vessel = self
                    .vessels
                    .iter()
                    .find(|vessel| vessel.id == *id)
                    .ok_or_else(|| format!("unknown vessel '{id}'"))?;
                // Restricted to passive traffic on purpose: the flagship and
                // scouts are core to the mission, not test debris. Every
                // vessel this command exists to clean up (scenario spawns
                // from FleetCore Control Center, manual test spawns) is
                // spawn-passive-contact's own output, so this is genuinely
                // the symmetric inverse of that command, not a general
                // "remove anything" escape hatch.
                if vessel.kind != VesselKind::PassiveTraffic {
                    return Err(format!(
                        "cannot despawn '{id}': only passive-traffic contacts can be removed, not a {:?} vessel",
                        vessel.kind
                    ));
                }
                self.vessels.retain(|vessel| vessel.id != *id);
                "vessel-despawned"
            }
            Command::ResetFleet => {
                let sim_time = self.clock.sim_time();
                for condition in initial_conditions() {
                    if let Some(vessel) = self.vessel_mut(condition.id) {
                        vessel.position = condition.position;
                        vessel.course = normalize_degrees(condition.course);
                        vessel.speed_mps = condition.speed_mps;
                        vessel.route = condition.route;
                        vessel.route_id += 1;
                        vessel.status = VesselStatus::Underway;
                        vessel.last_update = sim_time.clone();
                    }
                    // A missing id (e.g. the flagship or a scout id was
                    // somehow renamed) is silently skipped rather than
                    // erroring the whole command -- resetting the other
                    // three vessels is still better than resetting none of
                    // them, and there's no world in which the flagship
                    // itself is ever absent to explain to an operator.
                }
                "fleet-reset"
            }
            Command::SetEscortMode { mode } => {
                self.escort_mode = *mode;
                if *mode == EscortMode::Off {
                    // Hold position cleanly rather than coasting toward a
                    // stale station point -- see advance_vessel, where a
                    // scout with an empty route just sits still.
                    let sim_time = self.clock.sim_time();
                    for vessel in &mut self.vessels {
                        if vessel.kind == VesselKind::Scout {
                            vessel.route.clear();
                            vessel.status = VesselStatus::Holding;
                            vessel.last_update = sim_time.clone();
                        }
                    }
                }
                "escort-mode-set"
            }
            Command::RecordWatchEvent { message } => {
                self.watch_events.push(WatchEvent {
                    tick: self.clock.tick,
                    sim_time: self.clock.sim_time(),
                    message: message.clone(),
                });
                "watch-event-recorded"
            }
            Command::Step { ticks } => {
                self.step(*ticks);
                "world-stepped"
            }
        }
        .to_string();

        self.event_sequence += 1;
        Ok(Event {
            sequence: self.event_sequence,
            tick: self.clock.tick,
            event_type,
            command,
            sim_time: self.clock.sim_time(),
        })
    }

    pub fn replay_event(&mut self, event: &Event) -> Result<(), String> {
        let applied = self.apply_command(event.command.clone())?;
        if applied.sequence != event.sequence
            || applied.tick != event.tick
            || applied.event_type != event.event_type
        {
            return Err(format!(
                "event replay mismatch at sequence {}: expected {} at tick {}, got {} at tick {}",
                event.sequence, event.event_type, event.tick, applied.event_type, applied.tick
            ));
        }
        Ok(())
    }

    pub fn step(&mut self, ticks: u64) {
        if !self.clock.is_running() {
            return;
        }
        for _ in 0..ticks {
            for _ in 0..self.clock.time_scale {
                self.advance_one_tick();
            }
        }
    }

    fn advance_one_tick(&mut self) {
        self.clock.tick += 1;
        let sim_time = self.clock.sim_time();
        let tick_duration = self.clock.tick_duration_seconds as f64;

        // Re-issue every scout's route to a freshly computed station point
        // before the normal physics pass below -- reuses advance_vessel's
        // existing route-chasing motion instead of a separate movement
        // path, so escorts never run out of a target the way a one-shot
        // route would.
        if self.escort_mode != EscortMode::Off {
            let mode = self.escort_mode;
            let tick = self.clock.tick;
            if let Some(leader) = self
                .vessels
                .iter()
                .find(|vessel| vessel.kind == VesselKind::Flagship)
                .cloned()
            {
                let scout_ids: Vec<String> = self
                    .vessels
                    .iter()
                    .filter(|vessel| vessel.kind == VesselKind::Scout)
                    .map(|vessel| vessel.id.clone())
                    .collect();
                let slot_count = scout_ids.len();
                for (index, id) in scout_ids.iter().enumerate() {
                    let station = escort_station(&leader, index, slot_count, mode, tick);
                    if let Some(vessel) = self.vessel_mut(id) {
                        vessel.route = vec![station];
                        vessel.status = VesselStatus::Underway;
                    }
                }
            }
        }

        let tick = self.clock.tick;
        for vessel in &mut self.vessels {
            if let Some(event) = advance_vessel(vessel, tick_duration, &sim_time, tick) {
                self.vessel_events.push(event);
            }
        }
    }

    fn vessel_mut(&mut self, id: &str) -> Option<&mut Vessel> {
        self.vessels.iter_mut().find(|vessel| vessel.id == id)
    }
}

// Returns the VesselEvent for this vessel's transition this tick, if any --
// at most one, per the "mutually exclusive, no blending" rule. A vessel
// that's still en route to its current target (the final `else` branch of
// the "still traveling" case) doesn't get an event every tick, only on an
// actual leg/route completion.
fn advance_vessel(
    vessel: &mut Vessel,
    elapsed_seconds: f64,
    sim_time: &str,
    tick: u64,
) -> Option<VesselEvent> {
    if vessel.speed_mps <= 0.0 {
        return None;
    }

    if let Some(target) = vessel.route.first().copied() {
        let remaining = distance_meters(vessel.position, target);
        if remaining <= ARRIVAL_RADIUS_METERS {
            vessel.position = target;
            vessel.route.remove(0);
            vessel.last_update = sim_time.to_string();
            return Some(leg_or_route_complete(vessel, target, tick, sim_time));
        }

        vessel.course = quantize(bearing_degrees(vessel.position, target));
        let step = vessel.speed_mps * elapsed_seconds;
        if step >= remaining {
            vessel.position = target;
            vessel.route.remove(0);
            vessel.last_update = sim_time.to_string();
            return Some(leg_or_route_complete(vessel, target, tick, sim_time));
        }
        vessel.position = point_at_distance(vessel.position, vessel.course, step);
        vessel.status = VesselStatus::Underway;
        vessel.last_update = sim_time.to_string();
        return None;
    }

    if vessel.kind == VesselKind::PassiveTraffic {
        vessel.position = point_at_distance(
            vessel.position,
            vessel.course,
            vessel.speed_mps * elapsed_seconds,
        );
        vessel.status = VesselStatus::Transiting;
        vessel.last_update = sim_time.to_string();
    }
    None
}

// Shared by both arrival paths in advance_vessel (the immediate-snap case
// and the step-overshoots-remaining case) -- same event logic either way,
// just reached via a different distance check.
fn leg_or_route_complete(
    vessel: &mut Vessel,
    reached_waypoint: Position,
    tick: u64,
    sim_time: &str,
) -> VesselEvent {
    if vessel.route.is_empty() {
        vessel.status = VesselStatus::Arrived;
        VesselEvent::RouteCompleted {
            vessel_id: vessel.id.clone(),
            route_id: vessel.route_id,
            tick,
            sim_time: sim_time.to_string(),
        }
    } else {
        vessel.status = VesselStatus::Underway;
        VesselEvent::WaypointReached {
            vessel_id: vessel.id.clone(),
            route_id: vessel.route_id,
            waypoint: reached_waypoint,
            remaining_leg_count: vessel.route.len(),
            tick,
            sim_time: sim_time.to_string(),
        }
    }
}

struct InitialCondition {
    id: &'static str,
    position: Position,
    course: f64,
    speed_mps: f64,
    route: Vec<Position>,
}

// The flagship's and each scout's starting position, course, speed, and
// route -- deliberately the exact same values as fleetcore/data/seed-
// world.json's own vessels, not new numbers invented for this command.
// Kept as a hardcoded constant here (rather than reading seed-world.json
// at reset time) because World::apply_command has no file I/O anywhere
// else and stays a pure in-memory state transition; if seed-world.json's
// starting positions are ever deliberately changed, update both together.
// Passive-traffic contacts are untouched by reset-fleet on purpose --
// despawn-vessel already exists for those, and initial conditions were
// asked for "Monad and escorts" specifically.
fn initial_conditions() -> Vec<InitialCondition> {
    vec![
        InitialCondition {
            id: "vessel.monad",
            position: Position { lat: 26.56, lng: 56.25 },
            course: 270.0,
            speed_mps: 20.0,
            route: vec![Position { lat: 26.25, lng: 55.35 }],
        },
        InitialCondition {
            id: "vessel.scout-alpha",
            position: Position { lat: 26.34, lng: 55.93 },
            course: 286.0,
            speed_mps: 18.0,
            route: vec![Position { lat: 26.3, lng: 55.7 }],
        },
        InitialCondition {
            id: "vessel.scout-bravo",
            position: Position { lat: 26.54, lng: 56.63 },
            course: 238.0,
            speed_mps: 17.0,
            route: vec![Position { lat: 26.47, lng: 56.36 }],
        },
        InitialCondition {
            id: "vessel.scout-charlie",
            position: Position { lat: 26.74, lng: 56.31 },
            course: 204.0,
            speed_mps: 16.0,
            route: vec![Position { lat: 26.58, lng: 56.15 }],
        },
    ]
}
