use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
pub enum CanonEntityKind {
    Crew,
    Agent,
    Station,
    Department,
    Vessel,
    Contact,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct CanonEntity {
    pub id: String,
    pub kind: CanonEntityKind,
    pub name: String,
    #[serde(default)]
    pub aliases: Vec<String>,
    #[serde(default)]
    pub onboarding_status: Option<String>,
    #[serde(default)]
    pub merged_into: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct CanonAssignment {
    pub id: String,
    pub subject_id: String,
    pub assignment_type: String,
    pub value: String,
    #[serde(default)]
    pub active: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct CanonClaim {
    pub id: String,
    pub subject_id: String,
    pub capability: String,
    pub verified: bool,
    #[serde(default)]
    pub active: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct CanonPermission {
    pub id: String,
    pub subject_id: String,
    pub permission: String,
    pub approved_by: String,
    #[serde(default)]
    pub active: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct CanonRelationship {
    pub id: String,
    pub subject_id: String,
    pub relationship: String,
    pub object_id: String,
    #[serde(default)]
    pub active: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct AuthorizationRecord {
    pub id: String,
    pub subject_id: String,
    pub request: String,
    pub status: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct CanonProvenance {
    pub source_id: String,
    pub source_hash: String,
    pub assertion_id: String,
    pub adjudication_id: String,
    pub adjudicator: String,
    pub adjudicated_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(tag = "change", rename_all = "kebab-case")]
pub enum CanonChange {
    CreateEntity {
        entity: CanonEntity,
    },
    AddAlias {
        entity_id: String,
        alias: String,
    },
    Assign {
        assignment: CanonAssignment,
    },
    SetOnboardingStatus {
        entity_id: String,
        status: String,
    },
    AttachCapability {
        claim: CanonClaim,
    },
    CreateRelationship {
        relationship: CanonRelationship,
    },
    RecordAuthorization {
        authorization: AuthorizationRecord,
    },
    GrantPermission {
        permission: CanonPermission,
    },
    RevokeAssignment {
        assignment_id: String,
    },
    RemovePermission {
        permission_id: String,
    },
    MergeEntity {
        entity_id: String,
        into_entity_id: String,
    },
    CorrectLocation {
        assignment_id: String,
        location: String,
    },
    DowngradeClaim {
        claim_id: String,
    },
    SupersedeEvent {
        event_id: String,
    },
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct CanonEvent {
    pub id: String,
    pub command_id: String,
    pub fleet_event_sequence: u64,
    pub change: CanonChange,
    pub provenance: CanonProvenance,
    #[serde(default)]
    pub superseded: bool,
}
