use fleetcore::canon::{
    CanonAssignment, CanonChange, CanonClaim, CanonEntity, CanonEntityKind, CanonPermission,
    CanonProvenance,
};
use fleetcore::command::Command;
use fleetcore::persistence::{load_seed, load_world, save_world, StorePaths};
use fleetcore::snapshot::snapshot;
use std::path::PathBuf;

fn world() -> (StorePaths, fleetcore::world::World) {
    let dir = std::env::temp_dir().join(format!("fleetcore-canon-{}", std::process::id()));
    let paths = StorePaths::new(
        dir,
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("data/seed-world.json"),
    );
    let world = load_seed(&paths).unwrap();
    (paths, world)
}

fn provenance(assertion: &str) -> CanonProvenance {
    CanonProvenance {
        source_id: "source.first-wave".into(),
        source_hash: "sha256:abc".into(),
        assertion_id: assertion.into(),
        adjudication_id: format!("review.{assertion}"),
        adjudicator: "captain".into(),
        adjudicated_at: "2026-07-14T00:00:00Z".into(),
    }
}

fn apply(
    world: &mut fleetcore::world::World,
    id: &str,
    change: CanonChange,
) -> fleetcore::event::Event {
    world
        .apply_command(Command::ApplyCanonChange {
            command_id: id.into(),
            change,
            provenance: provenance(id),
        })
        .unwrap()
}

#[test]
fn canon_changes_are_validated_idempotent_exposed_and_persisted() {
    let (paths, mut world) = world();
    apply(
        &mut world,
        "cmd.create",
        CanonChange::CreateEntity {
            entity: CanonEntity {
                id: "crew.vance".into(),
                kind: CanonEntityKind::Crew,
                name: "Vance".into(),
                aliases: vec![],
                onboarding_status: None,
                merged_into: None,
            },
        },
    );
    apply(
        &mut world,
        "cmd.assign",
        CanonChange::Assign {
            assignment: CanonAssignment {
                id: "assignment.vance.scram".into(),
                subject_id: "crew.vance".into(),
                assignment_type: "role".into(),
                value: "scram watch".into(),
                active: false,
            },
        },
    );
    apply(
        &mut world,
        "cmd.claim",
        CanonChange::AttachCapability {
            claim: CanonClaim {
                id: "claim.vance.radiation".into(),
                subject_id: "crew.vance".into(),
                capability: "radiation immunity".into(),
                verified: false,
                active: false,
            },
        },
    );
    let duplicate = apply(
        &mut world,
        "cmd.assign",
        CanonChange::Assign {
            assignment: CanonAssignment {
                id: "ignored".into(),
                subject_id: "crew.vance".into(),
                assignment_type: "role".into(),
                value: "duplicate".into(),
                active: false,
            },
        },
    );
    assert_eq!(duplicate.event_type, "canon-command-duplicate");
    assert_eq!(world.canon_assignments.len(), 1);
    assert_eq!(world.canon_events.len(), 3);
    assert!(!world.canon_claims[0].verified);
    assert_eq!(
        snapshot(&world).canon_events[1].provenance.source_id,
        "source.first-wave"
    );
    save_world(&paths, &world).unwrap();
    let restored = load_world(&paths).unwrap();
    assert_eq!(restored.canon_events, world.canon_events);
    let _ = std::fs::remove_dir_all(paths.state_dir);
}

#[test]
fn permission_requires_explicit_matching_approver_and_corrections_preserve_history() {
    let (_, mut world) = world();
    apply(
        &mut world,
        "cmd.create",
        CanonChange::CreateEntity {
            entity: CanonEntity {
                id: "crew.vance".into(),
                kind: CanonEntityKind::Crew,
                name: "Vance".into(),
                aliases: vec![],
                onboarding_status: None,
                merged_into: None,
            },
        },
    );
    let rejected = world.apply_command(Command::ApplyCanonChange {
        command_id: "cmd.permission.bad".into(),
        change: CanonChange::GrantPermission {
            permission: CanonPermission {
                id: "permission.scram".into(),
                subject_id: "crew.vance".into(),
                permission: "reactor scram".into(),
                approved_by: "model".into(),
                active: false,
            },
        },
        provenance: provenance("permission"),
    });
    assert!(rejected.unwrap_err().contains("approver"));
    apply(
        &mut world,
        "cmd.station",
        CanonChange::Assign {
            assignment: CanonAssignment {
                id: "assignment.station".into(),
                subject_id: "crew.vance".into(),
                assignment_type: "station".into(),
                value: "Deck 6".into(),
                active: false,
            },
        },
    );
    apply(
        &mut world,
        "cmd.correct",
        CanonChange::CorrectLocation {
            assignment_id: "assignment.station".into(),
            location: "Deck 7".into(),
        },
    );
    assert_eq!(world.canon_assignments.len(), 2);
    assert!(!world.canon_assignments[0].active);
    assert!(world.canon_assignments[1].active);
}

#[test]
fn old_world_json_defaults_canon_state() {
    let (_, world) = world();
    assert!(world.canon_entities.is_empty());
    assert!(world.canon_events.is_empty());
}

#[test]
fn intake_compiler_wire_shape_deserializes_as_a_canon_command() {
    let payload = serde_json::json!({
        "type": "apply-canon-change",
        "command_id": "cmd_fixture_assignment",
        "change": {
            "change": "assign",
            "assignment": {
                "id": "assignment_fixture_ada",
                "subject_id": "crew.ada",
                "assignment_type": "role",
                "value": "Reactor Analyst",
                "active": true
            }
        },
        "provenance": {
            "source_id": "src_fixture",
            "source_hash": "d93f35da05397263a7464f0e",
            "assertion_id": "ast_fixture",
            "adjudication_id": "adj_fixture",
            "adjudicator": "Captain",
            "adjudicated_at": "2026-07-14T00:00:00Z"
        }
    });
    let command: Command = serde_json::from_value(payload).expect("intake wire command");
    assert!(matches!(command, Command::ApplyCanonChange { .. }));
}
