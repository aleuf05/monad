use crate::vessel::Position;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(tag = "type", rename_all = "kebab-case")]
pub enum Command {
    SetRoute {
        vessel_id: String,
        route: Vec<Position>,
    },
    PauseClock,
    ResumeClock,
    SetTimeScale {
        scale: u32,
    },
    SpawnPassiveContact {
        id: String,
        name: String,
        callsign: String,
        position: Position,
        course: f64,
        speed_mps: f64,
    },
    DespawnVessel {
        id: String,
    },
    ResetFleet,
    RecordWatchEvent {
        message: String,
    },
    Step {
        ticks: u64,
    },
}
