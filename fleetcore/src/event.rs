use crate::command::Command;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Event {
    pub sequence: u64,
    pub tick: u64,
    pub event_type: String,
    pub command: Command,
    pub sim_time: String,
}
