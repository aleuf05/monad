use crate::vessel::Position;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
pub enum EscortPosture {
    HoldStation,
    AdvanceScreen,
    WidenFlank,
    CoverRear,
    InvestigateContact,
    RecoverFormation,
    EmergencySeparation,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq, Default)]
#[serde(rename_all = "kebab-case")]
pub enum CaptainRuntimeStatus {
    #[default]
    Idle,
    Observing,
    Deciding,
    Fallback,
    Error,
    Disabled,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct CaptainControl {
    pub captain_id: String,
    pub vessel_id: String,
    pub role: String,
    pub enabled: bool,
    pub runtime_status: CaptainRuntimeStatus,
    pub provider: String,
    pub status_message: String,
    pub last_report_tick: Option<u64>,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
pub enum DecisionOutcome {
    Accepted,
    Rejected,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct AgentDecisionRecord {
    pub decision_id: String,
    pub captain_id: String,
    pub vessel_id: String,
    pub posture: EscortPosture,
    pub target_contact_id: Option<String>,
    pub objective: String,
    pub assessment: String,
    pub observed_tick: u64,
    pub observed_event_sequence: u64,
    pub submitted_tick: u64,
    pub sim_time: String,
    pub reconsider_at_tick: u64,
    pub outcome: DecisionOutcome,
    pub result: String,
    #[serde(default)]
    pub executed_tick: Option<u64>,
    #[serde(default)]
    pub target: Option<Position>,
    #[serde(default)]
    pub consequence: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct EscortIntent {
    pub decision_id: String,
    pub captain_id: String,
    pub vessel_id: String,
    pub posture: EscortPosture,
    pub target_contact_id: Option<String>,
    pub objective: String,
    pub assessment: String,
    pub reconsider_at_tick: u64,
    pub accepted_tick: u64,
    pub executed_tick: Option<u64>,
    pub last_target: Option<Position>,
    pub consequence: Option<String>,
}

pub fn default_captain(vessel_id: &str) -> Option<CaptainControl> {
    let (captain_id, role) = match vessel_id {
        "vessel.scout-alpha" => ("captain.alpha", "Forward screen and reconnaissance"),
        "vessel.scout-bravo" => ("captain.bravo", "Flank security and maneuvering room"),
        "vessel.scout-charlie" => ("captain.charlie", "Rear guard and formation integrity"),
        _ => return None,
    };
    Some(CaptainControl {
        captain_id: captain_id.to_string(),
        vessel_id: vessel_id.to_string(),
        role: role.to_string(),
        enabled: true,
        runtime_status: CaptainRuntimeStatus::Idle,
        provider: "not-connected".to_string(),
        status_message: "Awaiting captain runtime.".to_string(),
        last_report_tick: None,
    })
}
