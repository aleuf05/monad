use crate::clock::{ClockState, WorldClock};
use crate::command::Command;
use crate::event::Event;
use crate::geography;
use crate::route::{bearing_degrees, distance_meters, point_at_distance};
use crate::vessel::{normalize_degrees, quantize, Vessel, VesselKind, VesselStatus};
use serde::{Deserialize, Serialize};

const ARRIVAL_RADIUS_METERS: f64 = 80.0;

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
                if let Some(waypoint) = route
                    .iter()
                    .find(|point| geography::is_on_land(point))
                {
                    let zone = geography::zone_containing(waypoint).expect("is_on_land just confirmed a match");
                    return Err(format!(
                        "route rejected: waypoint ({}, {}) is on land ({})",
                        waypoint.lat, waypoint.lng, zone.name
                    ));
                }
                let sim_time = self.clock.sim_time();
                let vessel = self
                    .vessel_mut(vessel_id)
                    .ok_or_else(|| format!("unknown vessel '{vessel_id}'"))?;
                vessel.route = route.clone();
                vessel.status = if vessel.route.is_empty() {
                    VesselStatus::Holding
                } else {
                    VesselStatus::Underway
                };
                vessel.last_update = sim_time;
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
                };
                vessel.normalize();
                self.vessels.push(vessel);
                self.vessels.sort_by(|a, b| a.id.cmp(&b.id));
                "passive-contact-spawned"
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
        for vessel in &mut self.vessels {
            advance_vessel(vessel, tick_duration, &sim_time);
        }
    }

    fn vessel_mut(&mut self, id: &str) -> Option<&mut Vessel> {
        self.vessels.iter_mut().find(|vessel| vessel.id == id)
    }
}

fn advance_vessel(vessel: &mut Vessel, elapsed_seconds: f64, sim_time: &str) {
    if vessel.speed_mps <= 0.0 {
        return;
    }

    if let Some(target) = vessel.route.first().copied() {
        let remaining = distance_meters(vessel.position, target);
        if remaining <= ARRIVAL_RADIUS_METERS {
            vessel.position = target;
            vessel.route.remove(0);
            vessel.status = if vessel.route.is_empty() {
                VesselStatus::Arrived
            } else {
                VesselStatus::Underway
            };
            vessel.last_update = sim_time.to_string();
            return;
        }

        vessel.course = quantize(bearing_degrees(vessel.position, target));
        let step = vessel.speed_mps * elapsed_seconds;
        if step >= remaining {
            vessel.position = target;
            vessel.route.remove(0);
            vessel.status = if vessel.route.is_empty() {
                VesselStatus::Arrived
            } else {
                VesselStatus::Underway
            };
        } else {
            vessel.position = point_at_distance(vessel.position, vessel.course, step);
            vessel.status = VesselStatus::Underway;
        }
        vessel.last_update = sim_time.to_string();
        return;
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
}
