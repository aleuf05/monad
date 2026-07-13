use crate::agent::{CaptainRuntimeStatus, EscortPosture};
use crate::vessel::{EscortMode, Position};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(tag = "type", rename_all = "kebab-case")]
pub enum Command {
    SetRoute {
        vessel_id: String,
        route: Vec<Position>,
    },
    SetEscortMode {
        mode: EscortMode,
    },
    SubmitEscortIntent {
        captain_id: String,
        vessel_id: String,
        posture: EscortPosture,
        target_contact_id: Option<String>,
        objective: String,
        assessment: String,
        observed_tick: u64,
        observed_event_sequence: u64,
        reconsider_at_tick: u64,
    },
    SetCaptainEnabled {
        vessel_id: String,
        enabled: bool,
    },
    SetAgentFleetPaused {
        paused: bool,
    },
    ReportCaptainRuntime {
        captain_id: String,
        vessel_id: String,
        status: CaptainRuntimeStatus,
        provider: String,
        message: String,
        observed_tick: u64,
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
