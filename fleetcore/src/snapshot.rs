use crate::geography::{self, LandZone};
use crate::vessel::EscortMode;
use crate::world::World;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct WorldSnapshot {
    pub schema_version: String,
    pub world_id: String,
    pub tick: u64,
    pub sim_time: String,
    pub clock_state: String,
    pub time_scale: u32,
    pub tick_duration_seconds: u64,
    pub vessels: Vec<crate::vessel::Vessel>,
    pub watch_events: Vec<crate::world::WatchEvent>,
    pub event_sequence: u64,
    pub escort_mode: EscortMode,
    // Static reference geography, not part of World's persisted state --
    // recomputed fresh on every snapshot rather than stored, so it costs
    // nothing to add here and never needs a migration. See geography.rs.
    pub land_zones: Vec<LandZone>,
}

pub fn snapshot(world: &World) -> WorldSnapshot {
    WorldSnapshot {
        schema_version: "monad.worldSnapshot.v1".to_string(),
        world_id: world.world_id.clone(),
        tick: world.clock.tick,
        sim_time: world.clock.sim_time(),
        clock_state: format!("{:?}", world.clock.state).to_lowercase(),
        time_scale: world.clock.time_scale,
        tick_duration_seconds: world.clock.tick_duration_seconds,
        vessels: world.vessels.clone(),
        watch_events: world.watch_events.clone(),
        event_sequence: world.event_sequence,
        escort_mode: world.escort_mode,
        land_zones: geography::land_zones(),
    }
}

pub fn snapshot_json(world: &World) -> Result<String, serde_json::Error> {
    serde_json::to_string_pretty(&snapshot(world)).map(|json| format!("{json}\n"))
}
