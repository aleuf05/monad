use fleetcore::command::Command;
use fleetcore::persistence::{
    append_event, load_seed, load_world, prune_checkpoints, read_events,
    replay_from_latest_checkpoint, save_checkpoint, save_world, StorePaths,
};
use fleetcore::snapshot::snapshot_json;
use fleetcore::vessel::Position;
use std::fs;
use std::path::PathBuf;

fn test_store() -> StorePaths {
    let mut state_dir = std::env::temp_dir();
    state_dir.push(format!(
        "fleetcore-determinism-{}",
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .expect("system time should be after unix epoch")
            .as_nanos()
    ));
    StorePaths::new(
        state_dir,
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("data/seed-world.json"),
    )
}

#[test]
fn checkpoint_plus_event_tail_replays_to_current_world() {
    let paths = test_store();
    fs::create_dir_all(&paths.state_dir).expect("state dir");
    let mut world = load_seed(&paths).expect("seed loads");
    save_world(&paths, &world).expect("initial world saves");

    let first = world
        .apply_command(Command::RecordWatchEvent {
            message: "checkpoint boundary".to_string(),
        })
        .expect("first command applies");
    append_event(&paths, &first).expect("first event appends");
    save_world(&paths, &world).expect("checkpoint world saves");
    save_checkpoint(&paths, &world).expect("checkpoint saves");

    for command in [
        Command::SetTimeScale { scale: 5 },
        Command::Step { ticks: 3 },
        Command::RecordWatchEvent {
            message: "tail replayed".to_string(),
        },
    ] {
        let event = world.apply_command(command).expect("tail command applies");
        append_event(&paths, &event).expect("tail event appends");
    }
    save_world(&paths, &world).expect("final world saves");

    let replayed = replay_from_latest_checkpoint(&paths, world.event_sequence)
        .expect("checkpoint replay succeeds")
        .expect("compatible checkpoint exists");
    assert_eq!(replayed.replayed_events, 3);
    assert_eq!(
        snapshot_json(&world).expect("current snapshot"),
        snapshot_json(&replayed.world).expect("replayed snapshot")
    );

    let _ = fs::remove_dir_all(&paths.state_dir);
}

#[test]
fn checkpoint_retention_keeps_newest_and_genesis() {
    let paths = test_store();
    fs::create_dir_all(&paths.checkpoints_dir).expect("checkpoint dir");
    for tick in [0, 10, 20, 30, 40] {
        fs::write(
            paths
                .checkpoints_dir
                .join(format!("checkpoint-tick-{tick:010}.json")),
            "{}",
        )
        .expect("checkpoint fixture");
    }

    prune_checkpoints(&paths, 2).expect("checkpoint pruning succeeds");
    let mut remaining = fs::read_dir(&paths.checkpoints_dir)
        .expect("checkpoint dir reads")
        .map(|entry| {
            entry
                .expect("checkpoint entry")
                .file_name()
                .to_string_lossy()
                .into_owned()
        })
        .collect::<Vec<_>>();
    remaining.sort();
    assert_eq!(
        remaining,
        vec![
            "checkpoint-tick-0000000000.json",
            "checkpoint-tick-0000000030.json",
            "checkpoint-tick-0000000040.json",
        ]
    );

    let _ = fs::remove_dir_all(&paths.state_dir);
}

#[test]
fn same_seed_events_and_ticks_replay_to_same_snapshot() {
    let paths = test_store();
    fs::create_dir_all(&paths.state_dir).expect("state dir");
    let original = load_seed(&paths).expect("seed loads");
    save_world(&paths, &original).expect("initial world saves");

    let commands = vec![
        Command::SetTimeScale { scale: 10 },
        Command::SetRoute {
            vessel_id: "vessel.monad".to_string(),
            route: vec![
                Position {
                    lat: 26.44,
                    lng: 55.9,
                },
                Position {
                    lat: 26.35,
                    lng: 55.55,
                },
            ],
        },
        Command::Step { ticks: 12 },
        Command::SpawnPassiveContact {
            id: "traffic.test-contact".to_string(),
            name: "Test Contact".to_string(),
            callsign: "TEST CONTACT".to_string(),
            // Moved from (26.1, 56.1) -- that point falls inside the
            // Musandam Peninsula land zone (geography.rs), which
            // World::apply_command now rejects. This is open water just
            // east of that zone; the exact position isn't otherwise
            // meaningful to what this test checks (determinism, not
            // geography).
            position: Position {
                lat: 25.5,
                lng: 58.0,
            },
            course: 91.0,
            speed_mps: 9.5,
        },
        Command::RecordWatchEvent {
            message: "Determinism test event.".to_string(),
        },
        Command::Step { ticks: 18 },
    ];

    for command in commands {
        let mut original = load_world(&paths).expect("world reloads between commands");
        let event = original.apply_command(command).expect("command applies");
        append_event(&paths, &event).expect("event appends");
        save_world(&paths, &original).expect("world saves between commands");
    }

    let original = load_world(&paths).expect("final world loads");

    let mut replayed = load_seed(&paths).expect("seed reloads");
    for event in read_events(&paths).expect("events load") {
        replayed.replay_event(&event).expect("event replays");
    }

    assert_eq!(
        snapshot_json(&original).expect("original snapshot"),
        snapshot_json(&replayed).expect("replayed snapshot")
    );

    let _ = fs::remove_dir_all(&paths.state_dir);
}
