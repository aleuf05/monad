use chrono::{DateTime, Duration, TimeZone, Utc};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "kebab-case")]
pub enum ClockState {
    Running,
    Paused,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct WorldClock {
    pub tick: u64,
    pub tick_duration_seconds: u64,
    pub time_scale: u32,
    pub state: ClockState,
    pub start_unix_seconds: i64,
}

impl WorldClock {
    pub fn sim_time(&self) -> String {
        let start = Utc
            .timestamp_opt(self.start_unix_seconds, 0)
            .single()
            .unwrap_or(DateTime::<Utc>::UNIX_EPOCH);
        let elapsed = Duration::seconds((self.tick * self.tick_duration_seconds) as i64);
        (start + elapsed).to_rfc3339_opts(chrono::SecondsFormat::Secs, true)
    }

    pub fn is_running(&self) -> bool {
        self.state == ClockState::Running
    }
}
