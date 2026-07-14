use crate::command::Command;
use crate::vessel::VesselEvent;
use serde::{Deserialize, Serialize};

fn legacy_event_schema() -> String {
    "monad.fleetcore.event.v1".to_string()
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct SequencedVesselEvent {
    pub sequence: u64,
    pub event: VesselEvent,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SubmissionMetadata {
    pub schema_version: String,
    pub idempotency_key: String,
    pub principal_id: String,
    pub principal_scope: String,
    pub command_digest: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Event {
    #[serde(default = "legacy_event_schema")]
    pub schema_version: String,
    pub sequence: u64,
    pub tick: u64,
    pub event_type: String,
    pub command: Command,
    pub sim_time: String,
    #[serde(default)]
    pub vessel_events: Vec<SequencedVesselEvent>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub submission: Option<SubmissionMetadata>,
}
