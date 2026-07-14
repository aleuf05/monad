use fleetcore::command::Command;
use fleetcore::persistence::{
    append_event, apply_authoritative, load_seed, restore_authoritative_world, save_world,
    StorePaths,
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

#[test]
fn one_command_allocates_unique_ordered_sequences_for_multiple_events() {
    let paths = store("multi");
    let mut world = load_seed(&paths).unwrap();
    for vessel in &mut world.vessels {
        vessel.route = vec![vessel.position];
    }

    let event = apply_authoritative(&paths, &mut world, Command::Step { ticks: 1 }).unwrap();
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
    let second = apply_authoritative(&paths, &mut world, Command::Step { ticks: 1 }).unwrap();
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

    let error = apply_authoritative(&paths, &mut world, Command::Step { ticks: 1 }).unwrap_err();
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
