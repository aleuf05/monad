use fleetcore::command::Command;
use fleetcore::persistence::{
    append_event, apply_authoritative, load_seed, read_events, require_v2_migration_marker,
    restore_authoritative_world, save_world, validate_event_log, StorePaths, SubmissionContext,
};
use std::fs;
use std::path::PathBuf;

fn store(label: &str) -> StorePaths {
    let state = std::env::temp_dir().join(format!(
        "fleetcore-{label}-{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    StorePaths::new(
        state,
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("data/seed-world.json"),
    )
}

fn submission(key: &str) -> SubmissionContext {
    SubmissionContext {
        idempotency_key: key.into(),
        principal_id: "test.commander".into(),
        principal_scope: "fleet.command".into(),
    }
}

#[test]
fn one_command_allocates_unique_ordered_sequences_for_multiple_events() {
    let paths = store("multi");
    let mut world = load_seed(&paths).unwrap();
    for vessel in &mut world.vessels {
        vessel.route = vec![vessel.position];
    }

    let event = apply_authoritative(
        &paths,
        &mut world,
        Command::Step { ticks: 1 },
        submission("multi.1"),
    )
    .unwrap()
    .event;
    assert!(event.vessel_events.len() > 1);
    assert_eq!(
        event
            .vessel_events
            .iter()
            .map(|event| event.sequence)
            .collect::<Vec<_>>(),
        (1..=event.vessel_events.len() as u64).collect::<Vec<_>>()
    );
    assert_eq!(
        world.vessel_event_next_sequence,
        event.vessel_events.len() as u64 + 1
    );
    for vessel in &mut world.vessels {
        vessel.route = vec![vessel.position];
    }
    let second = apply_authoritative(
        &paths,
        &mut world,
        Command::Step { ticks: 1 },
        submission("multi.2"),
    )
    .unwrap()
    .event;
    assert_eq!(
        second.vessel_events.first().unwrap().sequence,
        event.vessel_events.last().unwrap().sequence + 1
    );
    let _ = fs::remove_dir_all(paths.state_dir);
}

#[test]
fn append_failure_does_not_publish_candidate_mutation() {
    let paths = store("append-failure");
    fs::create_dir_all(&paths.events_path).unwrap();
    let mut world = load_seed(&paths).unwrap();
    let before = world.clone();

    let error = apply_authoritative(
        &paths,
        &mut world,
        Command::Step { ticks: 1 },
        submission("append.fail"),
    )
    .unwrap_err();
    assert!(error.starts_with("authoritative persistence failure:"));
    assert_eq!(world, before);
    let _ = fs::remove_dir_all(paths.state_dir);
}

#[test]
fn restart_replays_durable_log_ahead_of_world_and_restores_sequence_cursor() {
    let paths = store("restart");
    let mut persisted = load_seed(&paths).unwrap();
    save_world(&paths, &persisted).unwrap();

    let event = persisted.apply_command(Command::Step { ticks: 1 }).unwrap();
    append_event(&paths, &event).unwrap();
    let restored = restore_authoritative_world(&paths).unwrap();
    assert_eq!(restored, persisted);
    assert_eq!(
        restored.vessel_event_next_sequence,
        persisted.vessel_event_next_sequence
    );
    let _ = fs::remove_dir_all(paths.state_dir);
}

#[test]
fn replay_rejects_derived_event_mismatch() {
    let paths = store("replay");
    let mut original = load_seed(&paths).unwrap();
    for vessel in &mut original.vessels {
        vessel.route = vec![vessel.position];
    }
    let mut envelope = original.apply_command(Command::Step { ticks: 1 }).unwrap();
    assert!(!envelope.vessel_events.is_empty());
    envelope.vessel_events[0].sequence += 10;

    let mut replayed = load_seed(&paths).unwrap();
    for vessel in &mut replayed.vessels {
        vessel.route = vec![vessel.position];
    }
    assert!(replayed
        .replay_event(&envelope)
        .unwrap_err()
        .contains("derived vessel event replay mismatch"));
}

#[test]
fn save_failure_after_sync_is_reported_as_committed_and_recoverable() {
    let paths = store("save-after-commit");
    fs::create_dir_all(&paths.world_path).unwrap();
    let mut world = load_seed(&paths).unwrap();
    let before_sequence = world.event_sequence;
    let outcome = apply_authoritative(
        &paths,
        &mut world,
        Command::Step { ticks: 1 },
        submission("save.fail"),
    )
    .unwrap();
    assert!(!outcome.world_saved);
    assert!(outcome
        .degraded_cause
        .as_deref()
        .unwrap()
        .contains("after durable commit"));
    assert_eq!(world.event_sequence, before_sequence + 1);
    assert_eq!(read_events(&paths).unwrap(), vec![outcome.event]);
    fs::remove_dir_all(&paths.world_path).unwrap();
    save_world(&paths, &load_seed(&paths).unwrap()).unwrap();
    assert_eq!(restore_authoritative_world(&paths).unwrap(), world);
    let _ = fs::remove_dir_all(paths.state_dir);
}

#[test]
fn log_validation_rejects_gaps_even_when_world_sequence_is_caught_up() {
    let paths = store("gap");
    let mut world = load_seed(&paths).unwrap();
    let mut event = world.apply_command(Command::Step { ticks: 1 }).unwrap();
    event.sequence = 2;
    let error = validate_event_log(&paths, &[event]).unwrap_err();
    assert!(error.contains("expected sequence 1"));
}

#[test]
fn legacy_history_without_explicit_marker_refuses_v2_write_readiness() {
    let paths = store("marker");
    let mut world = load_seed(&paths).unwrap();
    world
        .vessel_events
        .push(fleetcore::vessel::VesselEvent::Holding {
            vessel_id: "vessel.monad".into(),
            tick: 1,
            sim_time: "2026-01-01T00:00:00Z".into(),
        });
    assert!(require_v2_migration_marker(&paths, &world, &[])
        .unwrap_err()
        .contains("explicit V2 migration marker"));
}

#[test]
fn lost_response_retry_returns_original_commit_without_mutation() {
    let paths = store("retry");
    let mut world = load_seed(&paths).unwrap();
    let first = apply_authoritative(
        &paths,
        &mut world,
        Command::Step { ticks: 1 },
        submission("retry.1"),
    )
    .unwrap();
    let after = world.clone();
    let retry = apply_authoritative(
        &paths,
        &mut world,
        Command::Step { ticks: 1 },
        submission("retry.1"),
    )
    .unwrap();
    assert!(retry.duplicate);
    assert_eq!(retry.event.sequence, first.event.sequence);
    assert_eq!(world, after);
    assert_eq!(read_events(&paths).unwrap().len(), 1);
    let _ = fs::remove_dir_all(paths.state_dir);
}

#[test]
fn key_collision_and_cross_principal_reuse_fail_closed() {
    let paths = store("collision");
    let mut world = load_seed(&paths).unwrap();
    apply_authoritative(
        &paths,
        &mut world,
        Command::Step { ticks: 1 },
        submission("owned.1"),
    )
    .unwrap();
    let after = world.clone();
    assert!(apply_authoritative(
        &paths,
        &mut world,
        Command::PauseClock,
        submission("owned.1")
    )
    .unwrap_err()
    .contains("different command"));
    let other = SubmissionContext {
        idempotency_key: "owned.1".into(),
        principal_id: "other.commander".into(),
        principal_scope: "fleet.command".into(),
    };
    assert!(
        apply_authoritative(&paths, &mut world, Command::Step { ticks: 1 }, other)
            .unwrap_err()
            .contains("different principal")
    );
    assert_eq!(world, after);
    assert_eq!(read_events(&paths).unwrap().len(), 1);
    let _ = fs::remove_dir_all(paths.state_dir);
}

#[test]
fn retry_identity_survives_restart_and_committed_degraded_save() {
    let paths = store("retry-restart");
    fs::create_dir_all(&paths.world_path).unwrap();
    let mut world = load_seed(&paths).unwrap();
    let first = apply_authoritative(
        &paths,
        &mut world,
        Command::Step { ticks: 1 },
        submission("durable.1"),
    )
    .unwrap();
    assert!(!first.world_saved);
    let retry = apply_authoritative(
        &paths,
        &mut world,
        Command::Step { ticks: 1 },
        submission("durable.1"),
    )
    .unwrap();
    assert!(retry.duplicate);
    assert_eq!(retry.event.sequence, first.event.sequence);
    fs::remove_dir_all(&paths.world_path).unwrap();
    save_world(&paths, &load_seed(&paths).unwrap()).unwrap();
    let mut restarted = restore_authoritative_world(&paths).unwrap();
    let before = restarted.clone();
    let retry = apply_authoritative(
        &paths,
        &mut restarted,
        Command::Step { ticks: 1 },
        submission("durable.1"),
    )
    .unwrap();
    assert!(retry.duplicate);
    assert_eq!(restarted, before);
    let _ = fs::remove_dir_all(paths.state_dir);
}

#[test]
fn intentional_repeated_steps_use_distinct_internal_style_keys() {
    let paths = store("intentional-repeat");
    let mut world = load_seed(&paths).unwrap();
    let first = apply_authoritative(
        &paths,
        &mut world,
        Command::Step { ticks: 1 },
        submission("internal.tick.1"),
    )
    .unwrap();
    let second = apply_authoritative(
        &paths,
        &mut world,
        Command::Step { ticks: 1 },
        submission("internal.tick.2"),
    )
    .unwrap();
    assert!(!first.duplicate && !second.duplicate);
    assert_eq!(second.event.sequence, first.event.sequence + 1);
    let _ = fs::remove_dir_all(paths.state_dir);
}
