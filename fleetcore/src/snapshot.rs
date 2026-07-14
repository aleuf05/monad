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
    pub vessel_events: Vec<crate::vessel::VesselEvent>,
    // Telemetry for GitHub issue #6's bounded vessel_events: the configured
    // retention (so clients/operators can see what's actually in effect,
    // not just assume a default) and the total count ever emitted (so a
    // gap between this and vessel_events.len() is visible at a glance). A
    // consumer detects it has fallen behind the retained window by
    // comparing its own last-seen event_seq against
    // vessel_events.first().event_seq, not from a separate field.
    pub vessel_event_retention: usize,
    pub vessel_events_emitted_total: u64,
    pub event_sequence: u64,
    pub escort_mode: EscortMode,
    pub agent_fleet_paused: bool,
    pub captain_controls: Vec<crate::agent::CaptainControl>,
    pub escort_intents: Vec<crate::agent::EscortIntent>,
    pub agent_decisions: Vec<crate::agent::AgentDecisionRecord>,
    pub canon_entities: Vec<crate::canon::CanonEntity>,
    pub canon_assignments: Vec<crate::canon::CanonAssignment>,
    pub canon_claims: Vec<crate::canon::CanonClaim>,
    pub canon_permissions: Vec<crate::canon::CanonPermission>,
    pub canon_relationships: Vec<crate::canon::CanonRelationship>,
    pub canon_authorizations: Vec<crate::canon::AuthorizationRecord>,
    pub canon_events: Vec<crate::canon::CanonEvent>,
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
        vessel_events: world.vessel_events.clone(),
        vessel_event_retention: world.vessel_event_retention,
        vessel_events_emitted_total: world.next_vessel_event_seq,
        event_sequence: world.event_sequence,
        escort_mode: world.escort_mode,
        agent_fleet_paused: world.agent_fleet_paused,
        captain_controls: world.captain_controls.clone(),
        escort_intents: world.escort_intents.clone(),
        agent_decisions: world.agent_decisions.clone(),
        canon_entities: world.canon_entities.clone(),
        canon_assignments: world.canon_assignments.clone(),
        canon_claims: world.canon_claims.clone(),
        canon_permissions: world.canon_permissions.clone(),
        canon_relationships: world.canon_relationships.clone(),
        canon_authorizations: world.canon_authorizations.clone(),
        canon_events: world.canon_events.clone(),
        land_zones: geography::land_zones(),
    }
}

pub fn snapshot_json(world: &World) -> Result<String, serde_json::Error> {
    serde_json::to_string_pretty(&snapshot(world)).map(|json| format!("{json}\n"))
}
