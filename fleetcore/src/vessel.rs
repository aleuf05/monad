use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq)]
pub struct Position {
    pub lat: f64,
    pub lng: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "kebab-case")]
pub enum VesselKind {
    Flagship,
    Scout,
    PassiveTraffic,
}

// Off leaves scouts under whatever route (or lack of one) they last had --
// see advance_vessel in world.rs, where a scout with an empty route simply
// holds position (unlike passive-traffic, which dead-reckons forever).
// Loose/Tight hold scouts at fixed bearings off the flagship's stern at
// different radii; Patrol uses the same radius as Loose but sweeps the
// relative bearing back and forth over time instead of holding a fixed
// slot. See escort_station() in world.rs for the actual geometry.
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Default)]
#[serde(rename_all = "kebab-case")]
pub enum EscortMode {
    #[default]
    Off,
    Loose,
    Patrol,
    Tight,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "kebab-case")]
pub enum VesselStatus {
    Holding,
    Underway,
    Paused,
    Transiting,
    Arrived,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Vessel {
    pub id: String,
    pub name: String,
    pub callsign: String,
    pub kind: VesselKind,
    pub position: Position,
    pub course: f64,
    pub speed_mps: f64,
    pub status: VesselStatus,
    pub route: Vec<Position>,
    pub last_update: String,
    // Identifies which route is currently installed -- bumped every time a
    // new route is set (SetRoute, ResetFleet), including on a fresh
    // assignment from Holding/Arrived, not just on a genuine replacement.
    // Escort Mode's own per-tick station-chasing (world.rs advance_one_tick)
    // writes vessel.route directly and deliberately does NOT bump this or
    // emit a VesselEvent -- that's continuous station-keeping, not an
    // operator route order, and treating every tick's station update as a
    // "replacement" would spam route_replaced constantly while escorting.
    // Defaulted for backward compat with state files saved before this
    // field existed -- 0 is a reasonable genesis value.
    #[serde(default)]
    pub route_id: u64,
}

impl Vessel {
    pub fn normalize(&mut self) {
        self.course = quantize(normalize_degrees(self.course));
        if self.speed_mps < 0.0 {
            self.speed_mps = 0.0;
        }
        self.position.lat = quantize(self.position.lat.clamp(-90.0, 90.0));
        self.position.lng = quantize(normalize_longitude(self.position.lng));
    }
}

// Per-vessel route/motion events, distinct from event::Event (which
// records the Command applied, for replay/persistence) and world::
// WatchEvent (free-text operator log lines). These are structured,
// mutually exclusive per tick per vessel -- a vessel gets at most one of
// these in a given tick -- so frontend status wording can derive purely
// from "what was the most recent event for this vessel" instead of
// re-inferring intent from status/route, which is what previously made a
// route replacement near an old waypoint indistinguishable from a real
// arrival. See world.rs's apply_command (SetRoute) and advance_vessel for
// where each variant is emitted.
// event_seq is a per-VesselEvent monotonic counter (World::next_vessel_event_seq),
// distinct from `tick`: multiple vessels can each push a VesselEvent within
// the same tick (the per-tick advance loop in world.rs iterates every
// vessel), so `tick` alone is not a unique or strictly-ordered cursor.
// event_seq is. Clients must cursor on event_seq, not array length or tick
// -- see docs/architecture/vessel-events-retention-investigation.md and
// GitHub issue #6. #[serde(default)] so state files saved before this field
// existed still load (defaulting to 0); World::normalize() detects that
// case and assigns fresh sequential values on load rather than leaving
// every old event at the same default.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum VesselEvent {
    WaypointReached {
        vessel_id: String,
        route_id: u64,
        waypoint: Position,
        remaining_leg_count: usize,
        tick: u64,
        sim_time: String,
        #[serde(default)]
        event_seq: u64,
    },
    RouteReplaced {
        vessel_id: String,
        old_route_id: u64,
        old_active_waypoint: Position,
        new_route_id: u64,
        new_first_waypoint: Position,
        remaining_leg_count: usize,
        // No real per-connection identity exists anywhere in fleetcore-serve
        // (see docs/deployment.md's "Known limitation" note -- there is no
        // auth at all, let alone identity). This is always "operator" today,
        // a placeholder, not a real actor id -- do not treat it as one.
        issuing_authority: String,
        tick: u64,
        sim_time: String,
        #[serde(default)]
        event_seq: u64,
    },
    RouteCompleted {
        vessel_id: String,
        route_id: u64,
        tick: u64,
        sim_time: String,
        #[serde(default)]
        event_seq: u64,
    },
    Holding {
        vessel_id: String,
        tick: u64,
        sim_time: String,
        #[serde(default)]
        event_seq: u64,
    },
}

impl VesselEvent {
    pub fn event_seq(&self) -> u64 {
        match self {
            VesselEvent::WaypointReached { event_seq, .. }
            | VesselEvent::RouteReplaced { event_seq, .. }
            | VesselEvent::RouteCompleted { event_seq, .. }
            | VesselEvent::Holding { event_seq, .. } => *event_seq,
        }
    }

    pub fn set_event_seq(&mut self, value: u64) {
        match self {
            VesselEvent::WaypointReached { event_seq, .. }
            | VesselEvent::RouteReplaced { event_seq, .. }
            | VesselEvent::RouteCompleted { event_seq, .. }
            | VesselEvent::Holding { event_seq, .. } => *event_seq = value,
        }
    }
}

pub fn quantize(value: f64) -> f64 {
    const SCALE: f64 = 1_000_000_000_000.0;
    (value * SCALE).round() / SCALE
}

pub fn normalize_degrees(value: f64) -> f64 {
    ((value % 360.0) + 360.0) % 360.0
}

pub fn normalize_longitude(value: f64) -> f64 {
    ((value + 540.0) % 360.0) - 180.0
}
