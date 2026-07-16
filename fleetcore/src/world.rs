use crate::agent::{
    default_captain, AgentDecisionRecord, CaptainControl, DecisionOutcome, EscortIntent,
    EscortPosture,
};
use crate::canon::{
    AuthorizationRecord, CanonAssignment, CanonChange, CanonClaim, CanonEntity, CanonEvent,
    CanonPermission, CanonProvenance, CanonRelationship,
};
use crate::clock::{ClockState, WorldClock};
use crate::command::Command;
use crate::event::Event;
use crate::geography;
use crate::route::{bearing_degrees, distance_meters, point_at_distance};
use crate::vessel::{
    normalize_degrees, quantize, EscortMode, Position, Vessel, VesselEvent, VesselKind,
    VesselStatus,
};
use serde::{Deserialize, Serialize};

const ARRIVAL_RADIUS_METERS: f64 = 80.0;

// Escort formation geometry: scouts are spread evenly across this many
// degrees, sorted by vessel id for a stable slot assignment. Radius varies
// by mode; Patrol reuses Loose's radius and adds a slow, deterministic
// bearing sweep on top of each slot's base offset, driven by tick count
// (not wall-clock time) so it stays replay-deterministic like everything
// else in this engine. Off/Loose/Patrol/Tight are centered dead astern
// (180 deg relative to the flagship's course); Screen is centered ahead
// instead -- see below.
const ESCORT_WEDGE_SPREAD_DEGREES: f64 = 70.0;
const ESCORT_LOOSE_RADIUS_METERS: f64 = 1200.0;
const ESCORT_TIGHT_RADIUS_METERS: f64 = 350.0;
const ESCORT_PATROL_SWEEP_DEGREES: f64 = 40.0;
const ESCORT_PATROL_SWEEP_RATE: f64 = 0.002;
// Screen anticipates the flagship's track: the station anchor is projected
// forward along the flagship's *current* course (not a full route lookahead
// -- advance_vessel already recomputes course toward the next waypoint every
// tick, so "current course" already means "the way it's actually headed").
// Scouts then take up the same wedge-plus-sweep pattern as Patrol around
// that forward anchor instead of around the flagship itself, so they lead
// rather than trail and keep weaving instead of holding a fixed point.
const ESCORT_SCREEN_LOOKAHEAD_METERS: f64 = 2500.0;
const ESCORT_SCREEN_RADIUS_METERS: f64 = 1200.0;
type AgentMovementPlan = (String, Position, Option<(String, String)>);

fn escort_station(
    leader: &Vessel,
    slot_index: usize,
    slot_count: usize,
    mode: EscortMode,
    tick: u64,
) -> Position {
    let slot_offset = if slot_count <= 1 {
        0.0
    } else {
        -ESCORT_WEDGE_SPREAD_DEGREES / 2.0
            + ESCORT_WEDGE_SPREAD_DEGREES * (slot_index as f64) / ((slot_count - 1) as f64)
    };
    let sweep = if mode == EscortMode::Patrol || mode == EscortMode::Screen {
        ESCORT_PATROL_SWEEP_DEGREES * ((tick as f64) * ESCORT_PATROL_SWEEP_RATE).sin()
    } else {
        0.0
    };
    if mode == EscortMode::Screen {
        let anchor = point_at_distance(leader.position, leader.course, ESCORT_SCREEN_LOOKAHEAD_METERS);
        let bearing = normalize_degrees(leader.course + slot_offset + sweep);
        return point_at_distance(anchor, bearing, ESCORT_SCREEN_RADIUS_METERS);
    }
    let radius = match mode {
        EscortMode::Tight => ESCORT_TIGHT_RADIUS_METERS,
        _ => ESCORT_LOOSE_RADIUS_METERS,
    };
    let bearing = normalize_degrees(leader.course + 180.0 + slot_offset + sweep);
    point_at_distance(leader.position, bearing, radius)
}

fn agent_station(
    leader: &Vessel,
    scout: &Vessel,
    slot_index: usize,
    slot_count: usize,
    intent: &EscortIntent,
    vessels: &[Vessel],
    tick: u64,
) -> (Position, String) {
    let slot_offset = if slot_count <= 1 {
        0.0
    } else {
        -ESCORT_WEDGE_SPREAD_DEGREES / 2.0
            + ESCORT_WEDGE_SPREAD_DEGREES * (slot_index as f64) / ((slot_count - 1) as f64)
    };
    let (target, description) = match intent.posture {
        EscortPosture::HoldStation => (
            escort_station(leader, slot_index, slot_count, EscortMode::Loose, tick),
            "holding assigned formation station".to_string(),
        ),
        EscortPosture::AdvanceScreen => (
            point_at_distance(
                leader.position,
                normalize_degrees(leader.course + slot_offset * 0.25),
                1_800.0,
            ),
            "advancing to a forward screening station".to_string(),
        ),
        EscortPosture::WidenFlank => {
            let side = if scout.id.contains("alpha") {
                -1.0
            } else {
                1.0
            };
            (
                point_at_distance(
                    leader.position,
                    normalize_degrees(leader.course + side * 90.0),
                    2_200.0,
                ),
                "opening lateral maneuvering room on the flank".to_string(),
            )
        }
        EscortPosture::CoverRear => (
            point_at_distance(
                leader.position,
                normalize_degrees(leader.course + 180.0 + slot_offset * 0.2),
                1_600.0,
            ),
            "covering the formation's rear sector".to_string(),
        ),
        EscortPosture::InvestigateContact => {
            let contact = intent
                .target_contact_id
                .as_ref()
                .and_then(|id| vessels.iter().find(|vessel| vessel.id == *id));
            match contact {
                Some(contact) => {
                    let contact_to_flagship = bearing_degrees(contact.position, leader.position);
                    (
                        point_at_distance(contact.position, contact_to_flagship, 650.0),
                        format!(
                            "closing {} to a deterministic 650 m observation stand-off",
                            contact.callsign
                        ),
                    )
                }
                None => (
                    escort_station(leader, slot_index, slot_count, EscortMode::Tight, tick),
                    "investigation target unavailable; recovering formation".to_string(),
                ),
            }
        }
        EscortPosture::RecoverFormation => (
            escort_station(leader, slot_index, slot_count, EscortMode::Tight, tick),
            "recovering to close formation".to_string(),
        ),
        EscortPosture::EmergencySeparation => {
            let nearest = vessels
                .iter()
                .filter(|other| other.id != scout.id)
                .min_by(|a, b| {
                    distance_meters(scout.position, a.position)
                        .total_cmp(&distance_meters(scout.position, b.position))
                });
            let escape_bearing = nearest
                .map(|other| {
                    normalize_degrees(bearing_degrees(scout.position, other.position) + 180.0)
                })
                .unwrap_or_else(|| normalize_degrees(leader.course + 90.0));
            (
                point_at_distance(scout.position, escape_bearing, 2_500.0),
                "creating deterministic emergency separation".to_string(),
            )
        }
    };

    if geography::is_on_land(&target) {
        (
            escort_station(leader, slot_index, slot_count, EscortMode::Tight, tick),
            format!("{description}; target intersected land, recovering formation instead"),
        )
    } else {
        (target, description)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct WatchEvent {
    pub tick: u64,
    pub sim_time: String,
    pub message: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct World {
    pub schema_version: String,
    pub world_id: String,
    pub clock: WorldClock,
    pub vessels: Vec<Vessel>,
    pub event_sequence: u64,
    pub watch_events: Vec<WatchEvent>,
    // Defaulted so seed/state files saved before this field existed still
    // load fine -- absent means Off, the pre-existing behavior.
    #[serde(default)]
    pub escort_mode: EscortMode,
    // Structured per-vessel route/motion events -- see VesselEvent's own
    // doc comment. Bounded to the newest `vessel_event_retention` entries
    // (GitHub issue #6) -- full history remains durable forever in the
    // separate, never-truncated events.jsonl command log; this field is a
    // derived, replay-reconstructible convenience view for live consumers,
    // not an independent source of history. Clients must cursor on each
    // event's own event_seq, not array length or tick (see
    // docs/architecture/vessel-events-retention-investigation.md).
    // Defaulted for backward compat with state files saved before this
    // existed.
    #[serde(default)]
    pub vessel_events: Vec<VesselEvent>,
    // Monotonic counter for VesselEvent::event_seq -- distinct from `tick`,
    // since multiple vessels can each push an event within one tick.
    // Persisted so it survives restart/replay without ever repeating a
    // value. Defaulted to 0 for old state files; World::normalize()
    // detects that case (0 counter, non-empty vessel_events) and assigns
    // fresh sequential values on load rather than leaving old events
    // uniformly at the same default.
    #[serde(default)]
    pub next_vessel_event_seq: u64,
    // How many of the newest vessel_events to retain in this field (and
    // therefore in world.json/checkpoints/live snapshots). Configurable via
    // fleetcore-serve's --vessel-event-retention flag, not hard-coded into
    // the protocol -- deliberately per Command ruling on GitHub issue #6.
    // Full history is unaffected either way; see the field comment above.
    #[serde(default = "default_vessel_event_retention")]
    pub vessel_event_retention: usize,
    #[serde(default)]
    pub agent_fleet_paused: bool,
    #[serde(default)]
    pub captain_controls: Vec<CaptainControl>,
    #[serde(default)]
    pub escort_intents: Vec<EscortIntent>,
    #[serde(default)]
    pub agent_decisions: Vec<AgentDecisionRecord>,
    #[serde(default)]
    pub canon_entities: Vec<CanonEntity>,
    #[serde(default)]
    pub canon_assignments: Vec<CanonAssignment>,
    #[serde(default)]
    pub canon_claims: Vec<CanonClaim>,
    #[serde(default)]
    pub canon_permissions: Vec<CanonPermission>,
    #[serde(default)]
    pub canon_relationships: Vec<CanonRelationship>,
    #[serde(default)]
    pub canon_authorizations: Vec<AuthorizationRecord>,
    #[serde(default)]
    pub canon_events: Vec<CanonEvent>,
}

// GitHub issue #6's approved default: generous relative to observed
// production rate (~2.8-3 events/tick) while removing nearly all growth.
// Configurable per-process via --vessel-event-retention; this is only the
// fallback for state files that predate the field or omit the flag.
pub fn default_vessel_event_retention() -> usize {
    2000
}

impl World {
    // Assigns the next monotonic event_seq, pushes, and trims to
    // vessel_event_retention -- the one place vessel_events is ever
    // mutated, so live ticking and replay (which both funnel through
    // apply_command) can never diverge on numbering or bounding.
    fn record_vessel_event(&mut self, mut event: VesselEvent) {
        event.set_event_seq(self.next_vessel_event_seq);
        self.next_vessel_event_seq += 1;
        self.vessel_events.push(event);
        if self.vessel_events.len() > self.vessel_event_retention {
            let excess = self.vessel_events.len() - self.vessel_event_retention;
            self.vessel_events.drain(0..excess);
        }
    }


    fn apply_canon_change(
        &mut self,
        command_id: &str,
        change: &CanonChange,
        provenance: &CanonProvenance,
    ) -> Result<&'static str, String> {
        fn required(label: &str, value: &str) -> Result<(), String> {
            if value.trim().is_empty() || value.len() > 500 {
                Err(format!("{label} must be non-empty and at most 500 bytes"))
            } else {
                Ok(())
            }
        }
        required("command_id", command_id)?;
        required("source_id", &provenance.source_id)?;
        required("source_hash", &provenance.source_hash)?;
        required("assertion_id", &provenance.assertion_id)?;
        required("adjudication_id", &provenance.adjudication_id)?;
        required("adjudicator", &provenance.adjudicator)?;
        required("adjudicated_at", &provenance.adjudicated_at)?;
        if self
            .canon_events
            .iter()
            .any(|event| event.command_id == command_id)
        {
            return Ok("canon-command-duplicate");
        }
        let entity_exists = |id: &str| {
            self.canon_entities
                .iter()
                .any(|entity| entity.id == id && entity.merged_into.is_none())
        };
        match change {
            CanonChange::CreateEntity { entity } => {
                required("entity id", &entity.id)?;
                required("entity name", &entity.name)?;
                if self
                    .canon_entities
                    .iter()
                    .any(|current| current.id == entity.id)
                {
                    return Err(format!("canon entity '{}' already exists", entity.id));
                }
                let mut entity = entity.clone();
                entity.aliases.sort();
                entity.aliases.dedup();
                self.canon_entities.push(entity);
            }
            CanonChange::AddAlias { entity_id, alias } => {
                required("alias", alias)?;
                let entity = self
                    .canon_entities
                    .iter_mut()
                    .find(|e| e.id == *entity_id && e.merged_into.is_none())
                    .ok_or_else(|| format!("unknown canon entity '{entity_id}'"))?;
                if !entity
                    .aliases
                    .iter()
                    .any(|current| current.eq_ignore_ascii_case(alias))
                {
                    entity.aliases.push(alias.trim().to_string());
                    entity.aliases.sort();
                }
            }
            CanonChange::Assign { assignment } => {
                if !entity_exists(&assignment.subject_id) {
                    return Err(format!(
                        "unknown assignment subject '{}'",
                        assignment.subject_id
                    ));
                }
                required("assignment id", &assignment.id)?;
                required("assignment type", &assignment.assignment_type)?;
                required("assignment value", &assignment.value)?;
                if self.canon_assignments.iter().any(|a| a.id == assignment.id) {
                    return Err(format!("assignment '{}' already exists", assignment.id));
                }
                let mut assignment = assignment.clone();
                assignment.active = true;
                self.canon_assignments.push(assignment);
            }
            CanonChange::SetOnboardingStatus { entity_id, status } => {
                required("onboarding status", status)?;
                self.canon_entities
                    .iter_mut()
                    .find(|e| e.id == *entity_id && e.merged_into.is_none())
                    .ok_or_else(|| format!("unknown canon entity '{entity_id}'"))?
                    .onboarding_status = Some(status.clone());
            }
            CanonChange::AttachCapability { claim } => {
                if !entity_exists(&claim.subject_id) {
                    return Err(format!("unknown capability subject '{}'", claim.subject_id));
                }
                if claim.verified {
                    return Err("capabilities must enter canon unverified; verification requires a later adjudicated change".to_string());
                }
                required("claim id", &claim.id)?;
                required("capability", &claim.capability)?;
                if self.canon_claims.iter().any(|c| c.id == claim.id) {
                    return Err(format!("claim '{}' already exists", claim.id));
                }
                let mut claim = claim.clone();
                claim.active = true;
                self.canon_claims.push(claim);
            }
            CanonChange::CreateRelationship { relationship } => {
                if !entity_exists(&relationship.subject_id)
                    || !entity_exists(&relationship.object_id)
                {
                    return Err(
                        "relationship endpoints must be existing canon entities".to_string()
                    );
                }
                required("relationship id", &relationship.id)?;
                required("relationship", &relationship.relationship)?;
                if self
                    .canon_relationships
                    .iter()
                    .any(|r| r.id == relationship.id)
                {
                    return Err(format!("relationship '{}' already exists", relationship.id));
                }
                let mut relationship = relationship.clone();
                relationship.active = true;
                self.canon_relationships.push(relationship);
            }
            CanonChange::RecordAuthorization { authorization } => {
                let vessel_exists = self
                    .vessels
                    .iter()
                    .any(|vessel| vessel.id == authorization.subject_id);
                if !entity_exists(&authorization.subject_id) && !vessel_exists {
                    return Err(format!(
                        "unknown authorization subject '{}'",
                        authorization.subject_id
                    ));
                }
                required("authorization id", &authorization.id)?;
                required("authorization request", &authorization.request)?;
                if !matches!(
                    authorization.status.as_str(),
                    "pending" | "approved" | "denied"
                ) {
                    return Err(
                        "authorization status must be pending, approved, or denied".to_string()
                    );
                }
                if self
                    .canon_authorizations
                    .iter()
                    .any(|a| a.id == authorization.id)
                {
                    return Err(format!(
                        "authorization '{}' already exists",
                        authorization.id
                    ));
                }
                self.canon_authorizations.push(authorization.clone());
            }
            CanonChange::GrantPermission { permission } => {
                if !entity_exists(&permission.subject_id) {
                    return Err(format!(
                        "unknown permission subject '{}'",
                        permission.subject_id
                    ));
                }
                required("permission id", &permission.id)?;
                required("permission", &permission.permission)?;
                required("permission approver", &permission.approved_by)?;
                if permission.approved_by != provenance.adjudicator {
                    return Err(
                        "permission approver must match the recorded adjudicator".to_string()
                    );
                }
                if self.canon_permissions.iter().any(|p| p.id == permission.id) {
                    return Err(format!("permission '{}' already exists", permission.id));
                }
                let mut permission = permission.clone();
                permission.active = true;
                self.canon_permissions.push(permission);
            }
            CanonChange::RevokeAssignment { assignment_id } => {
                self.canon_assignments
                    .iter_mut()
                    .find(|a| a.id == *assignment_id && a.active)
                    .ok_or_else(|| format!("unknown active assignment '{assignment_id}'"))?
                    .active = false
            }
            CanonChange::RemovePermission { permission_id } => {
                self.canon_permissions
                    .iter_mut()
                    .find(|p| p.id == *permission_id && p.active)
                    .ok_or_else(|| format!("unknown active permission '{permission_id}'"))?
                    .active = false
            }
            CanonChange::MergeEntity {
                entity_id,
                into_entity_id,
            } => {
                if entity_id == into_entity_id || !entity_exists(into_entity_id) {
                    return Err("entity merge requires two distinct existing entities".to_string());
                }
                self.canon_entities
                    .iter_mut()
                    .find(|e| e.id == *entity_id && e.merged_into.is_none())
                    .ok_or_else(|| format!("unknown canon entity '{entity_id}'"))?
                    .merged_into = Some(into_entity_id.clone());
            }
            CanonChange::CorrectLocation {
                assignment_id,
                location,
            } => {
                required("corrected location", location)?;
                let prior = self
                    .canon_assignments
                    .iter_mut()
                    .find(|a| a.id == *assignment_id && a.active && a.assignment_type == "station")
                    .ok_or_else(|| {
                        format!("unknown active station assignment '{assignment_id}'")
                    })?;
                prior.active = false;
                let mut corrected = prior.clone();
                corrected.id = format!("{assignment_id}.correction.{}", self.event_sequence + 1);
                corrected.value = location.clone();
                corrected.active = true;
                self.canon_assignments.push(corrected);
            }
            CanonChange::DowngradeClaim { claim_id } => {
                self.canon_claims
                    .iter_mut()
                    .find(|c| c.id == *claim_id && c.active)
                    .ok_or_else(|| format!("unknown active claim '{claim_id}'"))?
                    .verified = false
            }
            CanonChange::SupersedeEvent { event_id } => {
                self.canon_events
                    .iter_mut()
                    .find(|e| e.id == *event_id && !e.superseded)
                    .ok_or_else(|| format!("unknown active canon event '{event_id}'"))?
                    .superseded = true
            }
        }
        self.canon_entities.sort_by(|a, b| a.id.cmp(&b.id));
        self.canon_events.push(CanonEvent {
            id: format!("canon-event-{:08}", self.event_sequence + 1),
            command_id: command_id.to_string(),
            fleet_event_sequence: self.event_sequence + 1,
            change: change.clone(),
            provenance: provenance.clone(),
            superseded: false,
        });
        Ok("canon-change-applied")
    }

    pub fn normalize(&mut self) {
        for vessel in &mut self.vessels {
            vessel.normalize();
        }
        self.vessels.sort_by(|a, b| a.id.cmp(&b.id));
        let scout_ids: Vec<String> = self
            .vessels
            .iter()
            .filter(|vessel| vessel.kind == VesselKind::Scout)
            .map(|vessel| vessel.id.clone())
            .collect();
        for vessel_id in scout_ids {
            if !self
                .captain_controls
                .iter()
                .any(|control| control.vessel_id == vessel_id)
            {
                if let Some(control) = default_captain(&vessel_id) {
                    self.captain_controls.push(control);
                }
            }
        }
        self.captain_controls
            .sort_by(|a, b| a.vessel_id.cmp(&b.vessel_id));

        // Migration for state files saved before event_seq/retention existed:
        // next_vessel_event_seq defaults to 0 on load; a genuinely fresh
        // world also has an empty vessel_events, so "0 counter, non-empty
        // vessel_events" unambiguously means an old file. Assign fresh
        // sequential values in existing (already chronological) order
        // rather than leaving every old event at the same defaulted 0.
        if self.next_vessel_event_seq == 0 && !self.vessel_events.is_empty() {
            for (index, event) in self.vessel_events.iter_mut().enumerate() {
                event.set_event_seq(index as u64 + 1);
            }
            self.next_vessel_event_seq = self.vessel_events.len() as u64 + 1;
        }
        // Enforce the current retention bound on load too, so an
        // already-oversized world.json/checkpoint from before this change
        // shrinks on next load rather than staying oversized until the next
        // natural push-and-trim.
        if self.vessel_events.len() > self.vessel_event_retention {
            let excess = self.vessel_events.len() - self.vessel_event_retention;
            self.vessel_events.drain(0..excess);
        }
    }

    pub fn apply_command(&mut self, command: Command) -> Result<Event, String> {
        let event_type = match &command {
            Command::ApplyCanonChange { command_id, change, provenance } => {
                self.apply_canon_change(command_id, change, provenance)?
            }
            Command::SetRoute { vessel_id, route } => {
                // find_map (not find + a second zone_containing call) so
                // there's no separate .expect() that would panic -- and
                // therefore poison the Mutex<World> for every future
                // command -- if is_on_land and zone_containing ever
                // disagreed after a future refactor of either.
                if let Some((waypoint, zone)) = route
                    .iter()
                    .find_map(|point| geography::zone_containing(point).map(|zone| (point, zone)))
                {
                    return Err(format!(
                        "route rejected: waypoint ({}, {}) is on land ({})",
                        waypoint.lat, waypoint.lng, zone.name
                    ));
                }
                let tick = self.clock.tick;
                let sim_time = self.clock.sim_time();

                // Route replacement as a first-class event: a vessel that
                // was genuinely underway on a real route and gets a new one
                // holds its current position (no snap/jump), keeps moving
                // (status stays Underway), and gets its heading recomputed
                // toward the new first waypoint immediately -- it never
                // passes through Arrived/Holding on the way, which is what
                // previously let a same-tick replacement get misread
                // downstream as "arrived, then a new route was assigned"
                // instead of what actually happened, one continuous order.
                // A vessel that was NOT underway on a real route (Holding,
                // Arrived, Paused, or a scout with no route) gets a fresh
                // assignment instead -- there is nothing to replace.
                let event_to_emit: Option<VesselEvent> = {
                    let vessel = self
                        .vessel_mut(vessel_id)
                        .ok_or_else(|| format!("unknown vessel '{vessel_id}'"))?;
                    if route.is_empty() {
                        vessel.route = vec![];
                        vessel.status = VesselStatus::Holding;
                        vessel.last_update = sim_time.clone();
                        Some(VesselEvent::Holding {
                            vessel_id: vessel_id.clone(),
                            tick,
                            sim_time: sim_time.clone(),
                            event_seq: 0,
                        })
                    } else if vessel.status == VesselStatus::Underway && !vessel.route.is_empty() {
                        let old_route_id = vessel.route_id;
                        let old_active_waypoint = vessel.route[0];
                        vessel.route_id += 1;
                        vessel.route = route.clone();
                        vessel.course = quantize(bearing_degrees(vessel.position, route[0]));
                        vessel.status = VesselStatus::Underway;
                        vessel.last_update = sim_time.clone();
                        Some(VesselEvent::RouteReplaced {
                            vessel_id: vessel_id.clone(),
                            old_route_id,
                            old_active_waypoint,
                            new_route_id: vessel.route_id,
                            new_first_waypoint: route[0],
                            remaining_leg_count: route.len(),
                            issuing_authority: "operator".to_string(),
                            tick,
                            sim_time: sim_time.clone(),
                            event_seq: 0,
                        })
                    } else {
                        vessel.route_id += 1;
                        vessel.route = route.clone();
                        vessel.status = VesselStatus::Underway;
                        vessel.last_update = sim_time.clone();
                        None
                    }
                };
                if let Some(event) = event_to_emit {
                    self.record_vessel_event(event);
                }
                "route-set"
            }
            Command::PauseClock => {
                self.clock.state = ClockState::Paused;
                for vessel in &mut self.vessels {
                    if vessel.status == VesselStatus::Underway
                        || vessel.status == VesselStatus::Transiting
                    {
                        vessel.status = VesselStatus::Paused;
                        vessel.last_update = self.clock.sim_time();
                    }
                }
                "clock-paused"
            }
            Command::ResumeClock => {
                self.clock.state = ClockState::Running;
                let sim_time = self.clock.sim_time();
                for vessel in &mut self.vessels {
                    if vessel.status == VesselStatus::Paused {
                        vessel.status = if vessel.route.is_empty() {
                            VesselStatus::Transiting
                        } else {
                            VesselStatus::Underway
                        };
                        vessel.last_update = sim_time.clone();
                    }
                }
                "clock-resumed"
            }
            Command::SetTimeScale { scale } => {
                self.clock.time_scale = (*scale).clamp(1, 500);
                "time-scale-set"
            }
            Command::SpawnPassiveContact {
                id,
                name,
                callsign,
                position,
                course,
                speed_mps,
            } => {
                if self.vessels.iter().any(|vessel| vessel.id == *id) {
                    return Err(format!("vessel '{id}' already exists"));
                }
                if let Some(zone) = geography::zone_containing(position) {
                    return Err(format!(
                        "spawn rejected: position ({}, {}) is on land ({})",
                        position.lat, position.lng, zone.name
                    ));
                }
                let mut vessel = Vessel {
                    id: id.clone(),
                    name: name.clone(),
                    callsign: callsign.clone(),
                    kind: VesselKind::PassiveTraffic,
                    position: *position,
                    course: normalize_degrees(*course),
                    speed_mps: speed_mps.max(0.0),
                    status: VesselStatus::Transiting,
                    route: Vec::new(),
                    last_update: self.clock.sim_time(),
                    route_id: 0,
                    fuel_fraction: crate::vessel::default_fuel_fraction(),
                };
                vessel.normalize();
                self.vessels.push(vessel);
                self.vessels.sort_by(|a, b| a.id.cmp(&b.id));
                "passive-contact-spawned"
            }
            Command::DespawnVessel { id } => {
                let vessel = self
                    .vessels
                    .iter()
                    .find(|vessel| vessel.id == *id)
                    .ok_or_else(|| format!("unknown vessel '{id}'"))?;
                // Restricted to passive traffic on purpose: the flagship and
                // scouts are core to the mission, not test debris. Every
                // vessel this command exists to clean up (scenario spawns
                // from FleetCore Control Center, manual test spawns) is
                // spawn-passive-contact's own output, so this is genuinely
                // the symmetric inverse of that command, not a general
                // "remove anything" escape hatch.
                if vessel.kind != VesselKind::PassiveTraffic {
                    return Err(format!(
                        "cannot despawn '{id}': only passive-traffic contacts can be removed, not a {:?} vessel",
                        vessel.kind
                    ));
                }
                self.vessels.retain(|vessel| vessel.id != *id);
                "vessel-despawned"
            }
            Command::ResetFleet => {
                let sim_time = self.clock.sim_time();
                for condition in initial_conditions() {
                    if let Some(vessel) = self.vessel_mut(condition.id) {
                        vessel.position = condition.position;
                        vessel.course = normalize_degrees(condition.course);
                        vessel.speed_mps = condition.speed_mps;
                        vessel.route = condition.route;
                        vessel.route_id += 1;
                        vessel.status = VesselStatus::Underway;
                        vessel.last_update = sim_time.clone();
                        vessel.fuel_fraction = crate::vessel::default_fuel_fraction();
                    }
                    // A missing id (e.g. the flagship or a scout id was
                    // somehow renamed) is silently skipped rather than
                    // erroring the whole command -- resetting the other
                    // three vessels is still better than resetting none of
                    // them, and there's no world in which the flagship
                    // itself is ever absent to explain to an operator.
                }
                "fleet-reset"
            }
            Command::SetEscortMode { mode } => {
                let old_mode = self.escort_mode;
                self.escort_mode = *mode;
                if old_mode != *mode {
                    let sim_time = self.clock.sim_time();
                    let tick = self.clock.tick;
                    self.record_vessel_event(VesselEvent::EscortStationChanged {
                        vessel_id: "fleet".to_string(),
                        old_mode,
                        new_mode: *mode,
                        tick,
                        sim_time,
                        event_seq: 0,
                    });
                }
                if *mode == EscortMode::Off {
                    // Hold position cleanly rather than coasting toward a
                    // stale station point -- see advance_vessel, where a
                    // scout with an empty route just sits still.
                    let sim_time = self.clock.sim_time();
                    for vessel in &mut self.vessels {
                        if vessel.kind == VesselKind::Scout {
                            vessel.route.clear();
                            vessel.status = VesselStatus::Holding;
                            vessel.last_update = sim_time.clone();
                        }
                    }
                }
                "escort-mode-set"
            }
            Command::SubmitEscortIntent {
                captain_id,
                vessel_id,
                posture,
                target_contact_id,
                objective,
                assessment,
                observed_tick,
                observed_event_sequence,
                reconsider_at_tick,
            } => {
                let decision_id = format!("agent-decision-{:08}", self.event_sequence + 1);
                let mut rejection = None;
                let control = self
                    .captain_controls
                    .iter()
                    .find(|control| control.vessel_id == *vessel_id);
                match control {
                    None => rejection = Some(format!("no captain is assigned to '{vessel_id}'")),
                    Some(control) if control.captain_id != *captain_id => {
                        rejection = Some(format!(
                            "captain '{}' cannot command '{}'; assigned captain is '{}'",
                            captain_id, vessel_id, control.captain_id
                        ));
                    }
                    Some(control) if !control.enabled => {
                        rejection = Some(format!("captain '{}' is disabled", captain_id));
                    }
                    _ if self.agent_fleet_paused => {
                        rejection = Some("agent fleet is paused".to_string());
                    }
                    _ => {}
                }
                if rejection.is_none()
                    && !self
                        .vessels
                        .iter()
                        .any(|vessel| vessel.id == *vessel_id && vessel.kind == VesselKind::Scout)
                {
                    rejection = Some(format!("'{vessel_id}' is not a scout vessel"));
                }
                if rejection.is_none()
                    && (*observed_event_sequence > self.event_sequence
                        || self.event_sequence.saturating_sub(*observed_event_sequence) > 8
                        || *observed_tick > self.clock.tick)
                {
                    rejection = Some(format!(
                        "stale or future observation: tick {}, sequence {}; current tick {}, sequence {}",
                        observed_tick, observed_event_sequence, self.clock.tick, self.event_sequence
                    ));
                }
                if rejection.is_none()
                    && (objective.trim().is_empty()
                        || objective.len() > 240
                        || assessment.trim().is_empty()
                        || assessment.len() > 500)
                {
                    rejection = Some(
                        "objective and assessment must be non-empty and within size limits"
                            .to_string(),
                    );
                }
                if rejection.is_none()
                    && (*reconsider_at_tick <= self.clock.tick
                        || *reconsider_at_tick > self.clock.tick.saturating_add(10_000))
                {
                    rejection = Some(
                        "reconsider_at_tick must be in the near future (within 10,000 ticks)"
                            .to_string(),
                    );
                }
                if rejection.is_none() && *posture == EscortPosture::InvestigateContact {
                    match target_contact_id {
                        None => {
                            rejection = Some(
                                "investigate-contact requires target_contact_id".to_string(),
                            )
                        }
                        Some(target_id)
                            if !self.vessels.iter().any(|vessel| {
                                vessel.id == *target_id
                                    && vessel.kind == VesselKind::PassiveTraffic
                            }) =>
                        {
                            rejection = Some(format!(
                                "investigation target '{target_id}' is not a current passive contact"
                            ));
                        }
                        _ => {}
                    }
                }

                let (outcome, result, event_type) = if let Some(reason) = rejection {
                    (
                        DecisionOutcome::Rejected,
                        reason,
                        "escort-intent-rejected",
                    )
                } else {
                    let intent = EscortIntent {
                        decision_id: decision_id.clone(),
                        captain_id: captain_id.clone(),
                        vessel_id: vessel_id.clone(),
                        posture: *posture,
                        target_contact_id: target_contact_id.clone(),
                        objective: objective.trim().to_string(),
                        assessment: assessment.trim().to_string(),
                        reconsider_at_tick: *reconsider_at_tick,
                        accepted_tick: self.clock.tick,
                        executed_tick: None,
                        last_target: None,
                        consequence: None,
                    };
                    self.escort_intents
                        .retain(|current| current.vessel_id != *vessel_id);
                    self.escort_intents.push(intent);
                    self.escort_intents
                        .sort_by(|a, b| a.vessel_id.cmp(&b.vessel_id));
                    (
                        DecisionOutcome::Accepted,
                        "intent accepted for deterministic patrol execution".to_string(),
                        "escort-intent-accepted",
                    )
                };
                self.agent_decisions.push(AgentDecisionRecord {
                    decision_id,
                    captain_id: captain_id.clone(),
                    vessel_id: vessel_id.clone(),
                    posture: *posture,
                    target_contact_id: target_contact_id.clone(),
                    objective: objective.trim().to_string(),
                    assessment: assessment.trim().to_string(),
                    observed_tick: *observed_tick,
                    observed_event_sequence: *observed_event_sequence,
                    submitted_tick: self.clock.tick,
                    sim_time: self.clock.sim_time(),
                    reconsider_at_tick: *reconsider_at_tick,
                    outcome,
                    result,
                    executed_tick: None,
                    target: None,
                    consequence: None,
                });
                event_type
            }
            Command::SetCaptainEnabled { vessel_id, enabled } => {
                let control = self
                    .captain_controls
                    .iter_mut()
                    .find(|control| control.vessel_id == *vessel_id)
                    .ok_or_else(|| format!("no captain is assigned to '{vessel_id}'"))?;
                control.enabled = *enabled;
                if !*enabled {
                    control.runtime_status = crate::agent::CaptainRuntimeStatus::Disabled;
                    control.status_message = "Disabled by operator.".to_string();
                    self.escort_intents
                        .retain(|intent| intent.vessel_id != *vessel_id);
                } else if control.runtime_status == crate::agent::CaptainRuntimeStatus::Disabled {
                    control.runtime_status = crate::agent::CaptainRuntimeStatus::Idle;
                    control.status_message = "Enabled; awaiting next observation.".to_string();
                }
                "captain-enabled-set"
            }
            Command::SetAgentFleetPaused { paused } => {
                self.agent_fleet_paused = *paused;
                "agent-fleet-pause-set"
            }
            Command::ReportCaptainRuntime {
                captain_id,
                vessel_id,
                status,
                provider,
                message,
                observed_tick,
            } => {
                if *observed_tick > self.clock.tick {
                    return Err(format!(
                        "runtime report tick {} is ahead of world tick {}",
                        observed_tick, self.clock.tick
                    ));
                }
                if provider.len() > 80 || message.len() > 240 {
                    return Err("runtime report exceeds size limits".to_string());
                }
                let control = self
                    .captain_controls
                    .iter_mut()
                    .find(|control| control.vessel_id == *vessel_id)
                    .ok_or_else(|| format!("no captain is assigned to '{vessel_id}'"))?;
                if control.captain_id != *captain_id {
                    return Err(format!(
                        "captain '{}' cannot report for '{}'; assigned captain is '{}'",
                        captain_id, vessel_id, control.captain_id
                    ));
                }
                control.runtime_status = *status;
                control.provider = provider.trim().to_string();
                control.status_message = message.trim().to_string();
                control.last_report_tick = Some(*observed_tick);
                "captain-runtime-reported"
            }
            Command::RecordWatchEvent { message } => {
                self.watch_events.push(WatchEvent {
                    tick: self.clock.tick,
                    sim_time: self.clock.sim_time(),
                    message: message.clone(),
                });
                "watch-event-recorded"
            }
            Command::Step { ticks } => {
                self.step(*ticks);
                "world-stepped"
            }
        }
        .to_string();

        self.event_sequence += 1;
        Ok(Event {
            sequence: self.event_sequence,
            tick: self.clock.tick,
            event_type,
            command,
            sim_time: self.clock.sim_time(),
        })
    }

    pub fn replay_event(&mut self, event: &Event) -> Result<(), String> {
        let applied = self.apply_command(event.command.clone())?;
        if applied.sequence != event.sequence
            || applied.tick != event.tick
            || applied.event_type != event.event_type
        {
            return Err(format!(
                "event replay mismatch at sequence {}: expected {} at tick {}, got {} at tick {}",
                event.sequence, event.event_type, event.tick, applied.event_type, applied.tick
            ));
        }
        Ok(())
    }

    pub fn step(&mut self, ticks: u64) {
        if !self.clock.is_running() {
            return;
        }
        for _ in 0..ticks {
            for _ in 0..self.clock.time_scale {
                self.advance_one_tick();
            }
        }
    }

    fn advance_one_tick(&mut self) {
        self.clock.tick += 1;
        let tick = self.clock.tick;
        let sim_time = self.clock.sim_time();
        let tick_duration = self.clock.tick_duration_seconds as f64;

        // Translate bounded agent posture into a deterministic station target
        // before the normal physics pass. Captains never set routes directly:
        // they select posture, this layer resolves geometry/contact stand-off,
        // and advance_vessel remains the only movement implementation.
        if let Some(leader) = self
            .vessels
            .iter()
            .find(|vessel| vessel.kind == VesselKind::Flagship)
            .cloned()
        {
            let scout_ids: Vec<String> = self
                .vessels
                .iter()
                .filter(|vessel| vessel.kind == VesselKind::Scout)
                .map(|vessel| vessel.id.clone())
                .collect();
            let slot_count = scout_ids.len();
            let mut plans: Vec<AgentMovementPlan> = Vec::new();
            for (index, id) in scout_ids.iter().enumerate() {
                let scout = match self.vessels.iter().find(|vessel| vessel.id == *id) {
                    Some(scout) => scout,
                    None => continue,
                };
                let captain_enabled = self
                    .captain_controls
                    .iter()
                    .find(|control| control.vessel_id == *id)
                    .map(|control| control.enabled)
                    .unwrap_or(false);
                let intent = self
                    .escort_intents
                    .iter()
                    .find(|intent| intent.vessel_id == *id && intent.reconsider_at_tick >= tick);
                if !self.agent_fleet_paused && captain_enabled {
                    if let Some(intent) = intent {
                        let (target, consequence) = agent_station(
                            &leader,
                            scout,
                            index,
                            slot_count,
                            intent,
                            &self.vessels,
                            tick,
                        );
                        plans.push((
                            id.clone(),
                            target,
                            Some((intent.decision_id.clone(), consequence)),
                        ));
                        continue;
                    }
                }
                // Inference unavailable, captain disabled/paused, or intent
                // expired: preserve the existing deterministic escort mode.
                if self.escort_mode != EscortMode::Off {
                    plans.push((
                        id.clone(),
                        escort_station(&leader, index, slot_count, self.escort_mode, tick),
                        None,
                    ));
                }
            }
            for (id, target, agent_execution) in plans {
                if let Some(vessel) = self.vessel_mut(&id) {
                    vessel.route = vec![target];
                    vessel.status = VesselStatus::Underway;
                }
                if let Some((decision_id, consequence)) = agent_execution {
                    if let Some(intent) = self
                        .escort_intents
                        .iter_mut()
                        .find(|intent| intent.vessel_id == id && intent.decision_id == decision_id)
                    {
                        if intent.executed_tick.is_none() {
                            intent.executed_tick = Some(tick);
                            intent.consequence = Some(consequence.clone());
                        }
                        intent.last_target = Some(target);
                    }
                    if let Some(record) = self
                        .agent_decisions
                        .iter_mut()
                        .find(|record| record.decision_id == decision_id)
                    {
                        if record.executed_tick.is_none() {
                            record.executed_tick = Some(tick);
                            record.consequence = Some(consequence);
                        }
                        record.target = Some(target);
                    }
                }
            }
        }

        let mut emitted = Vec::new();
        for vessel in &mut self.vessels {
            let severity_before = crate::vessel::fuel_severity(vessel.fuel_fraction);
            if let Some(event) = advance_vessel(vessel, tick_duration, &sim_time, tick) {
                emitted.push(event);
            }
            let severity_after = crate::vessel::fuel_severity(vessel.fuel_fraction);
            if severity_after != severity_before {
                emitted.push(VesselEvent::FuelStatusChanged {
                    vessel_id: vessel.id.clone(),
                    old_severity: severity_before.to_string(),
                    new_severity: severity_after.to_string(),
                    fuel_fraction: vessel.fuel_fraction,
                    tick,
                    sim_time: sim_time.clone(),
                    event_seq: 0,
                });
            }
        }
        for event in emitted {
            self.record_vessel_event(event);
        }
    }

    fn vessel_mut(&mut self, id: &str) -> Option<&mut Vessel> {
        self.vessels.iter_mut().find(|vessel| vessel.id == id)
    }
}

// Returns the VesselEvent for this vessel's transition this tick, if any --
// at most one, per the "mutually exclusive, no blending" rule. A vessel
// that's still en route to its current target (the final `else` branch of
// the "still traveling" case) doesn't get an event every tick, only on an
// actual leg/route completion.
fn advance_vessel(
    vessel: &mut Vessel,
    elapsed_seconds: f64,
    sim_time: &str,
    tick: u64,
) -> Option<VesselEvent> {
    if vessel.speed_mps <= 0.0 {
        return None;
    }

    if let Some(target) = vessel.route.first().copied() {
        let remaining = distance_meters(vessel.position, target);
        if remaining <= ARRIVAL_RADIUS_METERS {
            vessel.deplete_fuel(remaining);
            vessel.position = target;
            vessel.route.remove(0);
            vessel.last_update = sim_time.to_string();
            return Some(leg_or_route_complete(vessel, target, tick, sim_time));
        }

        vessel.course = quantize(bearing_degrees(vessel.position, target));
        let step = vessel.speed_mps * elapsed_seconds;
        if step >= remaining {
            vessel.deplete_fuel(remaining);
            vessel.position = target;
            vessel.route.remove(0);
            vessel.last_update = sim_time.to_string();
            return Some(leg_or_route_complete(vessel, target, tick, sim_time));
        }
        vessel.deplete_fuel(step);
        vessel.position = point_at_distance(vessel.position, vessel.course, step);
        vessel.status = VesselStatus::Underway;
        vessel.last_update = sim_time.to_string();
        return None;
    }

    if vessel.kind == VesselKind::PassiveTraffic {
        let step = vessel.speed_mps * elapsed_seconds;
        vessel.deplete_fuel(step);
        vessel.position = point_at_distance(vessel.position, vessel.course, step);
        vessel.status = VesselStatus::Transiting;
        vessel.last_update = sim_time.to_string();
    }
    None
}

// Shared by both arrival paths in advance_vessel (the immediate-snap case
// and the step-overshoots-remaining case) -- same event logic either way,
// just reached via a different distance check.
fn leg_or_route_complete(
    vessel: &mut Vessel,
    reached_waypoint: Position,
    tick: u64,
    sim_time: &str,
) -> VesselEvent {
    if vessel.route.is_empty() {
        vessel.status = VesselStatus::Arrived;
        VesselEvent::RouteCompleted {
            vessel_id: vessel.id.clone(),
            route_id: vessel.route_id,
            tick,
            sim_time: sim_time.to_string(),
            event_seq: 0,
        }
    } else {
        vessel.status = VesselStatus::Underway;
        VesselEvent::WaypointReached {
            vessel_id: vessel.id.clone(),
            route_id: vessel.route_id,
            waypoint: reached_waypoint,
            remaining_leg_count: vessel.route.len(),
            tick,
            sim_time: sim_time.to_string(),
            event_seq: 0,
        }
    }
}

struct InitialCondition {
    id: &'static str,
    position: Position,
    course: f64,
    speed_mps: f64,
    route: Vec<Position>,
}

// The flagship's and each scout's starting position, course, speed, and
// route -- deliberately the exact same values as fleetcore/data/seed-
// world.json's own vessels, not new numbers invented for this command.
// Kept as a hardcoded constant here (rather than reading seed-world.json
// at reset time) because World::apply_command has no file I/O anywhere
// else and stays a pure in-memory state transition; if seed-world.json's
// starting positions are ever deliberately changed, update both together.
// Passive-traffic contacts are untouched by reset-fleet on purpose --
// despawn-vessel already exists for those, and initial conditions were
// asked for "Monad and escorts" specifically.
fn initial_conditions() -> Vec<InitialCondition> {
    vec![
        InitialCondition {
            id: "vessel.monad",
            position: Position {
                lat: 26.56,
                lng: 56.25,
            },
            course: 270.0,
            speed_mps: 20.0,
            route: vec![Position {
                lat: 26.25,
                lng: 55.35,
            }],
        },
        InitialCondition {
            id: "vessel.scout-alpha",
            position: Position {
                lat: 26.34,
                lng: 55.93,
            },
            course: 286.0,
            // Escorts must out-pace the flagship (1.4-1.6x its 20.0 m/s) to
            // actually be able to close distance and hold station -- see
            // escort_station()/advance_one_tick's per-tick station-chasing
            // above. A slower escort can never catch a continuously
            // receding target during sustained flagship transit.
            speed_mps: 32.0,
            route: vec![Position {
                lat: 26.3,
                lng: 55.7,
            }],
        },
        InitialCondition {
            id: "vessel.scout-bravo",
            position: Position {
                lat: 26.54,
                lng: 56.63,
            },
            course: 238.0,
            speed_mps: 30.0,
            route: vec![Position {
                lat: 26.47,
                lng: 56.36,
            }],
        },
        InitialCondition {
            id: "vessel.scout-charlie",
            position: Position {
                lat: 26.74,
                lng: 56.31,
            },
            course: 204.0,
            speed_mps: 28.0,
            route: vec![Position {
                lat: 26.58,
                lng: 56.15,
            }],
        },
    ]
}
