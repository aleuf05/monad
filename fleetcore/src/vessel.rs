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
